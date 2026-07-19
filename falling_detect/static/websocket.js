// static/websocket.js
(function() {
    // 防止重复初始化 WebSocket
    if (window.__ws_initialized) {
        console.log('⚠️ WebSocket 已初始化，跳过');
        return;
    }
    window.__ws_initialized = true;
    
    console.log('🚀 WebSocket 客户端初始化开始...');
    
    // ============================================================
    // 全局数据存储
    // ============================================================
    if (!window.__ws_data) {
        window.__ws_data = {
            alerts: [],
            devices: {},
            health: null,
            trend: null,
            history: null,
            messages: [],
            lastUpdate: null,
            connected: false,
            totalAlerts: 0
        };
    }
    
    // 回调函数列表
    if (!window.__ws_callbacks) {
        window.__ws_callbacks = [];
    }
    
    // 连接状态
    window.__ws_connected = false;
    window.__ws_reconnect_count = 0;
    window.__ws_max_reconnect = 10;
    
    // ============================================================
    // 【关键】定义所有函数，确保暴露到 window
    // ============================================================
    
    // 订阅数据更新
    window.wsSubscribe = function(callback) {
        if (typeof callback === 'function') {
            if (!window.__ws_callbacks) {
                window.__ws_callbacks = [];
            }
            window.__ws_callbacks.push(callback);
            console.log('📋 新增订阅者，当前订阅数:', window.__ws_callbacks.length);
            // 立即返回当前数据
            try {
                callback(null, window.__ws_data);
            } catch(e) {
                console.error('初始回调执行失败:', e);
            }
            return true;
        }
        console.warn('⚠️ wsSubscribe: 回调不是函数');
        return false;
    };
    
    // 取消订阅
    window.wsUnsubscribe = function(callback) {
        if (window.__ws_callbacks) {
            var index = window.__ws_callbacks.indexOf(callback);
            if (index > -1) {
                window.__ws_callbacks.splice(index, 1);
                console.log('📋 取消订阅，剩余订阅数:', window.__ws_callbacks.length);
                return true;
            }
        }
        return false;
    };
    
    // 获取当前数据
    window.wsGetData = function() {
        return window.__ws_data;
    };
    
    // 获取连接状态
    window.wsIsConnected = function() {
        return window.__ws_connected;
    };
    
    // 获取总告警数
    window.wsGetTotalAlerts = function() {
        return window.__ws_data ? window.__ws_data.alerts.length : 0;
    };
    
    // 发送消息
    window.wsSend = function(message) {
        if (window.__ws && window.__ws_connected) {
            try {
                if (typeof message === 'string') {
                    window.__ws.send(message);
                } else {
                    window.__ws.send(JSON.stringify(message));
                }
                return true;
            } catch(e) {
                console.error('发送消息失败:', e);
                return false;
            }
        } else {
            console.warn('⚠️ WebSocket 未连接，无法发送消息');
            return false;
        }
    };
    
    // ============================================================
    // 通知所有订阅者
    // ============================================================
    function notifyCallbacks(data) {
        if (window.__ws_callbacks && window.__ws_callbacks.length > 0) {
            console.log('📢 通知订阅者，数量:', window.__ws_callbacks.length);
            window.__ws_callbacks.forEach(function(callback) {
                try {
                    callback(data, window.__ws_data);
                } catch (e) {
                    console.error('回调执行失败:', e);
                }
            });
        }
    }
    
    // ============================================================
    // 触发页面更新
    // ============================================================
    function triggerPageUpdate() {
        try {
            var event = new CustomEvent('wsDataUpdate', {
                detail: { data: window.__ws_data, connected: window.__ws_connected }
            });
            window.dispatchEvent(event);
        } catch(e) {}
        notifyCallbacks(null);
    }
    
    // ============================================================
    // WebSocket 连接
    // ============================================================
    function connectWebSocket() {
        try {
            console.log('🔗 正在连接 WebSocket (尝试', window.__ws_reconnect_count + 1, '/', window.__ws_max_reconnect, ')...');
            
            const ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onopen = function() {
                window.__ws_connected = true;
                window.__ws_reconnect_count = 0;
                window.__ws_data.connected = true;
                console.log('✅ WebSocket 已连接');
                triggerPageUpdate();
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'alert') {
                        window.__ws_data.alerts.unshift(data);
                        window.__ws_data.totalAlerts = window.__ws_data.alerts.length;
                        if (window.__ws_data.alerts.length > 500) {
                            window.__ws_data.alerts = window.__ws_data.alerts.slice(0, 500);
                        }
                        console.log('📢 新增告警，当前总数:', window.__ws_data.alerts.length);
                    } else if (data.type === 'device_status') {
                        window.__ws_data.devices[data.device_id] = data;
                        console.log('📡 设备状态更新:', data.device_name, '->', data.status_text);
                    } else if (data.type === 'health_data') {
                        window.__ws_data.health = data;
                        console.log('❤️ 心理健康数据更新:', data.status);
                    } else if (data.type === 'trend_data') {
                        window.__ws_data.trend = data;
                        console.log('📈 趋势数据更新:', data.trend);
                    } else if (data.type === 'history_data') {
                        window.__ws_data.history = data;
                        console.log('📚 历史数据更新:', data.total, '条事件');
                    } else if (data.type === 'test') {
                        console.log('🧪 测试消息:', data.message);
                    }
                    
                    window.__ws_data.messages.push(data);
                    window.__ws_data.lastUpdate = new Date().toISOString();
                    window.__ws_data.connected = window.__ws_connected;
                    
                    triggerPageUpdate();
                    
                } catch (e) {
                    console.error('解析消息失败:', e, event.data);
                }
            };
            
            ws.onclose = function() {
                window.__ws_connected = false;
                window.__ws_data.connected = false;
                console.log('❌ WebSocket 断开');
                triggerPageUpdate();
                
                window.__ws_reconnect_count++;
                if (window.__ws_reconnect_count <= window.__ws_max_reconnect) {
                    var delay = Math.min(3000 * window.__ws_reconnect_count, 30000);
                    console.log('🔄 将在', delay/1000, '秒后重连...');
                    setTimeout(connectWebSocket, delay);
                } else {
                    console.error('❌ 已达到最大重连次数，停止重连');
                    window.__ws_data.error = '连接失败，请刷新页面重试';
                    triggerPageUpdate();
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket 错误:', error);
            };
            
            window.__ws = ws;
            
        } catch (e) {
            console.error('连接失败:', e);
            window.__ws_reconnect_count++;
            if (window.__ws_reconnect_count <= window.__ws_max_reconnect) {
                var delay = Math.min(3000 * window.__ws_reconnect_count, 30000);
                setTimeout(connectWebSocket, delay);
            }
        }
    }
    
    // ============================================================
    // 【关键】验证所有函数是否暴露
    // ============================================================
    function verifyFunctions() {
        var functions = {
            'wsSubscribe': typeof window.wsSubscribe === 'function',
            'wsUnsubscribe': typeof window.wsUnsubscribe === 'function',
            'wsGetData': typeof window.wsGetData === 'function',
            'wsIsConnected': typeof window.wsIsConnected === 'function',
            'wsSend': typeof window.wsSend === 'function'
        };
        
        console.log('✅ WebSocket 函数验证:');
        for (var key in functions) {
            console.log('  - ' + key + ':', functions[key] ? '✅' : '❌');
        }
        
        // 如果有函数未暴露，重新暴露
        if (!functions.wsSubscribe) {
            console.error('❌ wsSubscribe 未暴露！');
        }
        
        return functions;
    }
    
    // ============================================================
    // 启动连接
    // ============================================================
    setTimeout(function() {
        connectWebSocket();
        // 延迟验证
        setTimeout(verifyFunctions, 500);
        setTimeout(verifyFunctions, 1000);
    }, 300);
    
    console.log('🚀 WebSocket 客户端已初始化');
    console.log('📋 可用方法: wsSubscribe, wsUnsubscribe, wsGetData, wsIsConnected, wsSend');
    console.log('📊 当前数据:', window.__ws_data);
    
})();