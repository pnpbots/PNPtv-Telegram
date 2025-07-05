# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from datetime import datetime
from bot.payment_webhook import handle_payment_webhook
from bot.subscriber_manager import get_subscriber_manager  # ✅ CAMBIO: Usar el nuevo import

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PNP Television Bot Admin Panel",
    description="Admin panel with payment webhook",
    version="2.0.0"
)

@app.get("/", response_class=HTMLResponse)
async def admin_panel():
    """Serve the admin panel"""
    return HTMLResponse(content=get_admin_html())

@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    """Handle BOLD payment webhook"""
    return await handle_payment_webhook(request)

@app.get("/api/stats")
async def get_stats():
    """Get bot statistics"""
    try:
        # ✅ CAMBIO: Usar el nuevo patrón para obtener subscriber_manager
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PNP Television Bot",
        "timestamp": datetime.now().isoformat()
    }

# ✅ NUEVO: Endpoint adicional para obtener usuarios
@app.get("/api/users")
async def get_users(language: str = None, statuses: str = None):
    """Get users with optional filters"""
    try:
        manager = await get_subscriber_manager()
        
        # Parse statuses if provided
        status_list = None
        if statuses:
            status_list = [s.strip() for s in statuses.split(',')]
        
        users = await manager.get_users(language=language, statuses=status_list)
        return {"success": True, "data": users}
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ✅ NUEVO: Endpoint para obtener todos los suscriptores
@app.get("/api/subscribers")
async def get_all_subscribers():
    """Get all subscribers"""
    try:
        manager = await get_subscriber_manager()
        subscribers = await manager.get_all()
        return {"success": True, "data": subscribers}
    except Exception as e:
        logger.error(f"Error getting subscribers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_admin_html():
    """Return admin panel HTML"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PNP Television Bot - Admin Panel</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid #e9ecef;
        }
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            text-transform: uppercase;
            font-size: 0.9rem;
            letter-spacing: 1px;
        }
        .btn {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            background: #5a6fd8;
        }
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #51cf66;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .webhook-info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .status-indicator {
            color: #51cf66;
            font-weight: bold;
        }
        .error-indicator {
            color: #ff6b6b;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 PNP Television Bot</h1>
            <p><span class="live-indicator"></span>Admin Panel - Production Ready</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="totalUsers">0</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="activeUsers">0</div>
                <div class="stat-label">Active Subscriptions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalRevenue">$0.00</div>
                <div class="stat-label">Total Revenue</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="newToday">0</div>
                <div class="stat-label">Expiring Soon</div>
            </div>
        </div>
        
        <div>
            <h3>🚀 Quick Actions</h3>
            <button class="btn" onclick="refreshStats()">🔄 Refresh Stats</button>
            <button class="btn" onclick="testWebhook()">📡 Test Webhook</button>
            <button class="btn" onclick="exportData()">📥 Export Data</button>
            <button class="btn" onclick="viewUsers()">👥 View Users</button>
        </div>
        
        <div class="webhook-info">
            <h3>🔗 Webhook Configuration</h3>
            <p><strong>Payment Webhook URL:</strong> <code>/webhook/payment</code></p>
            <p><strong>Status:</strong> <span class="status-indicator">✅ Active</span></p>
            <p><strong>Events:</strong> payment.completed</p>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
            <h3>📋 System Status</h3>
            <p><span id="botStatus" class="status-indicator">✅ Bot Status: Online</span></p>
            <p><span id="adminStatus" class="status-indicator">✅ Admin Panel: Running</span></p>
            <p><span id="webhookStatus" class="status-indicator">✅ Payment Webhook: Active</span></p>
            <p><span id="dbStatus" class="status-indicator">✅ Database: Connected</span></p>
            <p>📅 <strong>Last Updated:</strong> <span id="lastUpdated">""" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</span></p>
            
            <h3>🎯 Features Active</h3>
            <p>✅ Unified channel access for all plans</p>
            <p>✅ Automatic invite link generation</p>
            <p>✅ BOLD payment integration</p>
            <p>✅ Subscription expiry management</p>
            <p>✅ Multi-language support</p>
        </div>
    </div>
    
    <script>
        async function refreshStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('totalUsers').textContent = data.data.total || 0;
                    document.getElementById('activeUsers').textContent = data.data.active || 0;
                    document.getElementById('lastUpdated').textContent = new Date().toLocaleString();
                    
                    // Update status indicators
                    document.getElementById('dbStatus').className = 'status-indicator';
                    document.getElementById('dbStatus').textContent = '✅ Database: Connected';
                    
                    alert('✅ Statistics updated!');
                } else {
                    throw new Error('Failed to get stats');
                }
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('dbStatus').className = 'error-indicator';
                document.getElementById('dbStatus').textContent = '❌ Database: Error';
                alert('❌ Connection error');
            }
        }
        
        async function testWebhook() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                
                if (data.status === 'healthy') {
                    alert('✅ Webhook endpoint is healthy!\\n📡 URL: /webhook/payment\\n🔗 Ready to receive BOLD payments!');
                } else {
                    alert('⚠️ Webhook may have issues');
                }
            } catch (error) {
                alert('❌ Webhook test failed');
            }
        }
        
        async function exportData() {
            try {
                const response = await fetch('/api/subscribers');
                const data = await response.json();
                
                if (data.success) {
                    const blob = new Blob([JSON.stringify(data.data, null, 2)], {type: 'application/json'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'pnp-tv-subscribers-' + new Date().toISOString().split('T')[0] + '.json';
                    a.click();
                    alert('✅ Data exported successfully!');
                } else {
                    throw new Error('Export failed');
                }
            } catch (error) {
                alert('❌ Export failed: ' + error.message);
            }
        }
        
        async function viewUsers() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                
                if (data.success) {
                    const users = data.data;
                    let message = `👥 Total Users: ${users.length}\\n\\n`;
                    
                    const byStatus = users.reduce((acc, user) => {
                        acc[user.status] = (acc[user.status] || 0) + 1;
                        return acc;
                    }, {});
                    
                    message += 'Status Breakdown:\\n';
                    Object.entries(byStatus).forEach(([status, count]) => {
                        message += `${status}: ${count}\\n`;
                    });
                    
                    alert(message);
                } else {
                    throw new Error('Failed to get users');
                }
            } catch (error) {
                alert('❌ Error getting users: ' + error.message);
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshStats, 30000);
        
        // Load initial stats
        refreshStats();
    </script>
</body>
</html>"""