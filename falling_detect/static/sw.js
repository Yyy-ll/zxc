// static/sw.js

const CACHE_NAME = 'risk-events-v1';
const STORAGE_KEY = 'risk_events_data';

// ============================================================
// Service Worker 安装
// ============================================================
self.addEventListener('install', function(event) {
    console.log('[SW] 安装中...');
    self.skipWaiting();
});

// ============================================================
// Service Worker 激活
// ============================================================
self.addEventListener('activate', function(event) {
    console.log('[SW] 激活中...');
    event.waitUntil(clients.claim());
});

// ============================================================
// IndexedDB 操作
// ============================================================
function openDB() {
    return new Promise(function(resolve, reject) {
        const request = indexedDB.open('RiskEventDB', 2);
        
        request.onupgradeneeded = function(event) {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('events')) {
                const store = db.createObjectStore('events', { 
                    keyPath: 'id', 
                    autoIncrement: true 
                });
                store.createIndex('timestamp', 'timestamp', { unique: false });
                store.createIndex('alert_type', 'alert_type', { unique: false });
                store.createIndex('date', 'date', { unique: false });
            }
        };
        
        request.onsuccess = function(event) {
            resolve(event.target.result);
        };
        
        request.onerror = function(event) {
            reject(event.target.error);
        };
    });
}

// 保存事件到 IndexedDB
async function saveEventToDB(eventData) {
    try {
        const db = await openDB();
        const tx = db.transaction('events', 'readwrite');
        const store = tx.objectStore('events');
        
        // 添加日期字段用于按天查询
        const date = new Date().toDateString();
        const event = {
            ...eventData,
            date: date,
            savedAt: new Date().toISOString()
        };
        
        const result = await new Promise(function(resolve, reject) {
            const request = store.add(event);
            request.onsuccess = function() {
                resolve(request.result);
            };
            request.onerror = function() {
                reject(request.error);
            };
        });
        
        await tx.done;
        return result;
    } catch(e) {
        console.error('[SW] 保存事件失败:', e);
        return null;
    }
}

// 获取今天的事件
async function getTodayEvents() {
    try {
        const db = await openDB();
        const tx = db.transaction('events', 'readonly');
        const store = tx.objectStore('events');
        const index = store.index('date');
        
        const today = new Date().toDateString();
        const range = IDBKeyRange.only(today);
        
        const events = await new Promise(function(resolve, reject) {
            const request = index.getAll(range);
            request.onsuccess = function() {
                resolve(request.result);
            };
            request.onerror = function() {
                reject(request.error);
            };
        });
        
        return events || [];
    } catch(e) {
        console.error('[SW] 获取事件失败:', e);
        return [];
    }
}

// 清除昨天的数据（每天凌晨执行）
async function clearOldData() {
    try {
        const db = await openDB();
        const tx = db.transaction('events', 'readwrite');
        const store = tx.objectStore('events');
        const index = store.index('date');
        
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toDateString();
        const range = IDBKeyRange.only(yesterdayStr);
        
        const events = await new Promise(function(resolve, reject) {
            const request = index.getAll(range);
            request.onsuccess = function() {
                resolve(request.result);
            };
            request.onerror = function() {
                reject(request.error);
            };
        });
        
        for (const event of events) {
            await new Promise(function(resolve, reject) {
                const request = store.delete(event.id);
                request.onsuccess = resolve;
                request.onerror = reject;
            });
        }
        
        console.log('[SW] 已清除昨天的数据，共', events.length, '条');
    } catch(e) {
        console.error('[SW] 清除旧数据失败:', e);
    }
}

// ============================================================
// WebSocket 连接管理
// ============================================================
let ws = null;
let isConnected = false;
let reconnectTimer = null;

function connectWebSocket() {
    try {
        console.log('[SW] 🔗 连接 WebSocket...');
        ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = function() {
            isConnected = true;
            console.log('[SW] ✅ WebSocket 已连接');
            notifyClients({ type: 'connected' });
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('[SW] 📩 收到消息:', data.type);
                
                if (data.type === 'alert') {
                    // 保存到 IndexedDB
                    saveEventToDB(data).then(function(id) {
                        console.log('[SW] 💾 事件已保存到 IndexedDB, ID:', id);
                        // 通知所有客户端
                        notifyClients({
                            type: 'new_alert',
                            alert: data,
                            total: 0 // 客户端自己计算总数
                        });
                    });
                } else if (data.type === 'device_status') {
                    // 设备状态也保存
                    saveEventToDB(data);
                }
            } catch(e) {
                console.error('[SW] 解析消息失败:', e);
            }
        };
        
        ws.onclose = function() {
            isConnected = false;
            console.log('[SW] ❌ WebSocket 断开');
            notifyClients({ type: 'disconnected' });
            
            // 重连
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
            }
            reconnectTimer = setTimeout(function() {
                connectWebSocket();
            }, 3000);
        };
        
        ws.onerror = function(error) {
            console.error('[SW] WebSocket 错误:', error);
        };
        
    } catch(e) {
        console.error('[SW] 连接失败:', e);
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
        }
        reconnectTimer = setTimeout(function() {
            connectWebSocket();
        }, 3000);
    }
}

// ============================================================
// 通知所有客户端
// ============================================================
function notifyClients(message) {
    self.clients.matchAll().then(function(clients) {
        clients.forEach(function(client) {
            client.postMessage(message);
        });
    });
}

// ============================================================
// 监听来自页面的消息
// ============================================================
self.addEventListener('message', function(event) {
    const data = event.data;
    
    if (data.type === 'get_events') {
        // 页面请求获取所有事件
        getTodayEvents().then(function(events) {
            event.source.postMessage({
                type: 'events_data',
                events: events,
                connected: isConnected
            });
        });
    } else if (data.type === 'clear_old_data') {
        // 清除旧数据
        clearOldData();
    } else if (data.type === 'ping') {
        // 健康检查
        event.source.postMessage({
            type: 'pong',
            connected: isConnected
        });
    }
});

// ============================================================
// 每日自动清除（凌晨执行）
// ============================================================
function scheduleDailyClear() {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    const msUntilMidnight = tomorrow - now;
    
    console.log('[SW] ⏰ 将在', msUntilMidnight / 1000 / 60, '分钟后执行每日清除');
    
    setTimeout(function() {
        clearOldData();
        // 递归调度下一次
        scheduleDailyClear();
    }, msUntilMidnight);
}

// ============================================================
// 启动
// ============================================================
console.log('[SW] 🚀 Service Worker 启动');

// 连接 WebSocket
setTimeout(connectWebSocket, 1000);

// 启动每日清除
scheduleDailyClear();

console.log('[SW] ✅ Service Worker 已启动');