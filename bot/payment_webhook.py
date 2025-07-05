# -*- coding: utf-8 -*-
"""
WEBHOOK DE PAGOS MEJORADO CON SEGURIDAD
======================================
Sistema seguro de procesamiento de webhooks de Bold.co con validación y logging
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import hashlib
import hmac
import os
from datetime import datetime
from typing import Dict, Any

from bot.config import BOT_TOKEN, WEBHOOK_PORT
from bot.enhanced_subscriber_manager import get_subscriber_manager
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Configuración del webhook
app = FastAPI(title="PNP TV Payment Webhook", version="2.0")

# Configurar CORS para permitir requests de Bold.co
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios de Bold.co
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Bot instance
bot = Bot(token=BOT_TOKEN)

# Configuración de seguridad (opcional - depende de Bold.co)
WEBHOOK_SECRET = os.getenv("BOLD_WEBHOOK_SECRET")  # Secreto compartido con Bold.co

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verificar la firma del webhook si está configurada"""
    if not WEBHOOK_SECRET:
        logger.warning("BOLD_WEBHOOK_SECRET not configured - skipping signature verification")
        return True
    
    try:
        # Calcular firma esperada
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar firmas de forma segura
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False

async def process_payment_success(payment_data: Dict[str, Any]) -> Dict[str, str]:
    """Procesar pago exitoso de forma asíncrona"""
    try:
        # Extraer metadatos del pago
        metadata = payment_data.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_id = metadata.get('plan_id')
        transaction_id = payment_data.get('id', payment_data.get('transaction_id'))
        
        if not user_id or not plan_id:
            raise ValueError("Missing user_id or plan_id in payment metadata")
        
        user_id = int(user_id)
        
        # Obtener información del plan
        from bot.config import PLANS
        plan_info = None
        plan_name = None
        
        for key, info in PLANS.items():
            if key == plan_id:
                plan_info = info
                plan_name = info["name"]
                break
        
        if not plan_info:
            raise ValueError(f"Plan {plan_id} not found in configuration")
        
        # Registrar suscriptor
        manager = await get_subscriber_manager()
        success = await manager.add_subscriber(
            user_id=user_id,
            plan_name=plan_name,
            transaction_id=transaction_id
        )
        
        if not success:
            raise Exception("Failed to add subscriber to database")
        
        # Obtener idioma del usuario para el mensaje
        user_status = await manager.get_user_status(user_id)
        language = user_status.get('language', 'en')
        
        # Enviar confirmación al usuario
        if language == 'es':
            confirmation_message = f"""🎉 **¡Pago Confirmado!**

✅ **Suscripción activada exitosamente**
💎 **Plan:** {plan_name}
💰 **Precio:** {plan_info['price']}
⏱️ **Duración:** {plan_info['duration_days']} días
🆔 **Transacción:** {transaction_id}

🎬 **¡Ya tienes acceso a tus canales exclusivos!**
Los enlaces de invitación han sido enviados.

📧 **Soporte:** support@pnptv.app
💬 **Ayuda:** Envía cualquier mensaje a este bot"""
        else:
            confirmation_message = f"""🎉 **Payment Confirmed!**

✅ **Subscription activated successfully**
💎 **Plan:** {plan_name}
💰 **Price:** {plan_info['price']}
⏱️ **Duration:** {plan_info['duration_days']} days
🆔 **Transaction:** {transaction_id}

🎬 **You now have access to your exclusive channels!**
Invitation links have been sent.

📧 **Support:** support@pnptv.app
💬 **Help:** Send any message to this bot"""
        
        await bot.send_message(
            chat_id=user_id,
            text=confirmation_message,
            parse_mode='Markdown'
        )
        
        # Log del pago exitoso
        logger.info(f"Payment processed successfully: User {user_id}, Plan {plan_name}, Transaction {transaction_id}")
        
        return {
            "status": "success",
            "message": f"Subscription activated for user {user_id}",
            "user_id": str(user_id),
            "plan": plan_name,
            "transaction_id": transaction_id
        }
        
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        
        # Intentar notificar al usuario del error si tenemos su ID
        try:
            if 'user_id' in locals() and user_id:
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ **Error procesando tu pago**\n\n"
                         "Hemos recibido tu pago pero hubo un problema activando tu suscripción.\n"
                         "Nuestro equipo ha sido notificado y resolverá esto pronto.\n\n"
                         "📧 Contacta: support@pnptv.app\n"
                         f"🆔 Referencia: {transaction_id if 'transaction_id' in locals() else 'N/A'}",
                    parse_mode='Markdown'
                )
        except:
            pass
        
        raise

@app.get("/")
async def root():
    """Endpoint de salud del webhook"""
    return {
        "service": "PNP TV Payment Webhook",
        "status": "active",
        "version": "2.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint para Railway"""
    try:
        # Verificar conexión a la base de datos
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_users": stats.get('total', 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/webhook")
async def handle_payment_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Manejar webhook de pagos de Bold.co con seguridad mejorada
    """
    try:
        # Obtener el cuerpo de la request
        body = await request.body()
        
        # Verificar firma si está configurada
        signature = request.headers.get('X-Bold-Signature', '')
        if WEBHOOK_SECRET and not verify_webhook_signature(body, signature):
            logger.warning(f"Invalid webhook signature from IP: {request.client.host}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parsear JSON
        try:
            payment_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Log del webhook recibido
        logger.info(f"Webhook received from {request.client.host}: {payment_data.get('id', 'unknown')}")
        
        # Verificar que es un pago completado
        status = payment_data.get('status', '').lower()
        if status != 'completed':
            logger.info(f"Webhook ignored - status: {status}")
            return {"status": "ignored", "reason": f"Payment status is {status}"}
        
        # Procesar pago en background para respuesta rápida
        background_tasks.add_task(process_payment_success, payment_data)
        
        # Respuesta inmediata a Bold.co
        return {
            "status": "received",
            "message": "Payment webhook processed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/webhook/test")
async def test_webhook(request: Request):
    """Endpoint de prueba para el webhook (solo para desarrollo)"""
    if os.getenv("ENVIRONMENT") == "production":
        raise HTTPException(status_code=404, detail="Not found")
    
    body = await request.body()
    try:
        data = json.loads(body.decode('utf-8'))
        logger.info(f"Test webhook received: {data}")
        return {"status": "test_received", "data": data}
    except:
        return {"status": "test_received", "raw_body": body.decode('utf-8', errors='ignore')}

# Configuración para Railway
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", WEBHOOK_PORT))
    host = "0.0.0.0"  # Importante para Railway
    
    logger.info(f"Starting payment webhook server on {host}:{port}")
    
    uvicorn.run(
        "payment_webhook:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

