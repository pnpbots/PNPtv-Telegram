# -*- coding: utf-8 -*-
"""
WEBHOOK DE PAGOS MEJORADO CON SEGURIDAD Y VALIDACIONES
====================================================
Sistema robusto de procesamiento de webhooks de Bold.co con validación mejorada
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import json
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import asyncio

from bot.config import BOT_TOKEN, WEBHOOK_PORT, BOLD_WEBHOOK_SECRET, SECURITY_CONFIG
from bot.enhanced_subscriber_manager import get_subscriber_manager  # ✅ CORREGIDO: Import correcto
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Configuración del webhook con mejoras de seguridad
app = FastAPI(
    title="PNP TV Payment Webhook",
    description="Secure payment processing webhook with enhanced validation",
    version="2.0.1",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Configurar CORS de forma más restrictiva
allowed_origins = [
    "https://checkout.bold.co",
    "https://api.bold.co",
    "https://webhooks.bold.co",
]

# En desarrollo, permitir localhost
if os.getenv("ENVIRONMENT") != "production":
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Bot instance con configuración mejorada
bot = Bot(token=BOT_TOKEN)

# Security
security = HTTPBearer(auto_error=False)

# Rate limiting simple en memoria (en producción usar Redis)
webhook_calls = {}
RATE_LIMIT_WINDOW = 60  # segundos
RATE_LIMIT_MAX_CALLS = 100  # máximo calls por ventana

def check_rate_limit(client_ip: str) -> bool:
    """Verificar rate limiting básico"""
    now = datetime.now().timestamp()
    
    # Limpiar entradas antiguas
    for ip in list(webhook_calls.keys()):
        webhook_calls[ip] = [timestamp for timestamp in webhook_calls[ip] 
                           if now - timestamp < RATE_LIMIT_WINDOW]
        if not webhook_calls[ip]:
            del webhook_calls[ip]
    
    # Verificar límite para esta IP
    if client_ip not in webhook_calls:
        webhook_calls[client_ip] = []
    
    webhook_calls[client_ip].append(now)
    return len(webhook_calls[client_ip]) <= RATE_LIMIT_MAX_CALLS

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verificar firma del webhook con validación mejorada"""
    if not BOLD_WEBHOOK_SECRET:
        if SECURITY_CONFIG.get("require_webhook_signature", False):
            logger.error("Webhook signature required but BOLD_WEBHOOK_SECRET not configured")
            return False
        logger.warning("Webhook signature verification skipped - BOLD_WEBHOOK_SECRET not configured")
        return True
    
    if not signature:
        logger.warning("No signature provided in webhook request")
        return not SECURITY_CONFIG.get("require_webhook_signature", False)
    
    try:
        # Soportar diferentes formatos de firma
        if signature.startswith('sha256='):
            provided_signature = signature[7:]  # Remover prefijo 'sha256='
        else:
            provided_signature = signature
        
        # Calcular firma esperada
        expected_signature = hmac.new(
            BOLD_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar firmas de forma segura
        is_valid = hmac.compare_digest(expected_signature, provided_signature)
        
        if not is_valid:
            logger.warning(f"Invalid webhook signature. Expected: {expected_signature[:10]}..., Got: {provided_signature[:10]}...")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False

def validate_payment_data(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validar estructura de datos de pago"""
    required_fields = ['id', 'status', 'metadata']
    errors = []
    
    # Verificar campos requeridos
    for field in required_fields:
        if field not in payment_data:
            errors.append(f"Missing required field: {field}")
    
    # Validar metadata
    metadata = payment_data.get('metadata', {})
    if not isinstance(metadata, dict):
        errors.append("Metadata must be a dictionary")
    else:
        required_metadata = ['user_id', 'plan_id']
        for meta_field in required_metadata:
            if meta_field not in metadata:
                errors.append(f"Missing required metadata field: {meta_field}")
    
    # Validar tipos de datos
    if 'id' in payment_data and not isinstance(payment_data['id'], (str, int)):
        errors.append("Payment ID must be string or integer")
    
    if 'status' in payment_data and not isinstance(payment_data['status'], str):
        errors.append("Status must be string")
    
    # Validar user_id en metadata
    if 'metadata' in payment_data and 'user_id' in payment_data['metadata']:
        try:
            int(payment_data['metadata']['user_id'])
        except (ValueError, TypeError):
            errors.append("user_id in metadata must be a valid integer")
    
    if errors:
        raise ValueError(f"Payment data validation failed: {'; '.join(errors)}")
    
    return payment_data

async def process_payment_success(payment_data: Dict[str, Any]) -> Dict[str, str]:
    """Procesar pago exitoso con validaciones y logging mejorado"""
    processing_start = datetime.now(timezone.utc)
    
    try:
        # Validar datos de pago
        validated_data = validate_payment_data(payment_data)
        
        # Extraer metadatos con validación
        metadata = validated_data['metadata']
        user_id = int(metadata['user_id'])
        plan_id = str(metadata['plan_id'])
        transaction_id = str(validated_data['id'])
        
        # Datos adicionales del pago
        payment_amount = payment_data.get('amount')
        payment_currency = payment_data.get('currency', 'USD')
        
        logger.info(f"Processing payment: ID={transaction_id}, User={user_id}, Plan={plan_id}")
        
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
        
        # Procesar pago si no se especificó amount
        if payment_amount is None:
            payment_amount = float(plan_info["price"].replace("$", ""))
        else:
            payment_amount = float(payment_amount)
        
        # Registrar suscriptor con datos completos
        manager = await get_subscriber_manager()
        success = await manager.add_subscriber(
            user_id=user_id,
            plan_name=plan_name,
            transaction_id=transaction_id,
            payment_amount=payment_amount,
            payment_currency=payment_currency
        )
        
        if not success:
            raise Exception("Failed to add subscriber to database")
        
        # Obtener idioma del usuario para mensaje personalizado
        try:
            user_status = await manager.get_user_status(user_id)
            language = user_status.get('language', 'en')
        except Exception as e:
            logger.warning(f"Could not get user language for {user_id}: {e}")
            language = 'en'
        
        # Enviar confirmación personalizada al usuario
        success_message = await send_payment_confirmation(
            user_id, plan_info, transaction_id, language, payment_amount, payment_currency
        )
        
        # Calcular tiempo de procesamiento
        processing_time = (datetime.now(timezone.utc) - processing_start).total_seconds()
        
        # Log del pago exitoso con detalles completos
        logger.info(
            f"Payment processed successfully in {processing_time:.2f}s: "
            f"User={user_id}, Plan={plan_name}, Amount=${payment_amount:.2f}, "
            f"Transaction={transaction_id}"
        )
        
        # Notificar a administradores sobre pago importante (opcional)
        if payment_amount >= 100:  # Pagos grandes
            await notify_admins_large_payment(user_id, plan_name, payment_amount, transaction_id)
        
        return {
            "status": "success",
            "message": f"Subscription activated for user {user_id}",
            "user_id": str(user_id),
            "plan": plan_name,
            "transaction_id": transaction_id,
            "amount": f"${payment_amount:.2f}",
            "processing_time": f"{processing_time:.2f}s",
            "confirmation_sent": success_message
        }
        
    except ValueError as e:
        logger.error(f"Payment validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payment data: {e}")
        
    except Exception as e:
        logger.error(f"Error processing payment: {e}", exc_info=True)
        
        # Intentar notificar al usuario del error si tenemos su ID
        try:
            if 'user_id' in locals() and user_id:
                await send_payment_error_notification(user_id, transaction_id)
        except Exception as notify_error:
            logger.error(f"Failed to notify user of payment error: {notify_error}")
        
        # Notificar administradores del error crítico
        await notify_admins_payment_error(payment_data, str(e))
        
        raise HTTPException(status_code=500, detail="Payment processing failed")

async def send_payment_confirmation(user_id: int, plan_info: Dict, transaction_id: str, 
                                  language: str, amount: float, currency: str) -> bool:
    """Enviar confirmación de pago personalizada"""
    try:
        if language == 'es':
            confirmation_message = f"""🎉 **¡Pago Confirmado Exitosamente!**

✅ **Suscripción activada** 
💎 **Plan:** {plan_info['name']}
💰 **Cantidad:** ${amount:.2f} {currency}
⏱️ **Duración:** {plan_info['duration_days']} días
🆔 **Transacción:** `{transaction_id}`
📅 **Procesado:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

🎬 **¡Ya tienes acceso completo!**
Los enlaces de invitación a tus canales han sido enviados automáticamente.

📺 **Canales incluidos:** {len(plan_info.get('channels', []))}
🎯 **Contenido:** 200+ videos exclusivos
🎉 **Bonus:** Acceso a eventos virtuales

📧 **Soporte 24/7:** support@pnptv.app
💬 **Ayuda rápida:** Envía cualquier mensaje a este bot

¡Gracias por unirte a PNP Television! 🚀"""
        else:
            confirmation_message = f"""🎉 **Payment Confirmed Successfully!**

✅ **Subscription activated**
💎 **Plan:** {plan_info['name']}
💰 **Amount:** ${amount:.2f} {currency}
⏱️ **Duration:** {plan_info['duration_days']} days
🆔 **Transaction:** `{transaction_id}`
📅 **Processed:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

🎬 **You now have full access!**
Invitation links to your channels have been sent automatically.

📺 **Channels included:** {len(plan_info.get('channels', []))}
🎯 **Content:** 200+ exclusive videos
🎉 **Bonus:** Access to virtual events

📧 **24/7 Support:** support@pnptv.app
💬 **Quick help:** Send any message to this bot

Thank you for joining PNP Television! 🚀"""
        
        await bot.send_message(
            chat_id=user_id,
            text=confirmation_message,
            parse_mode='Markdown'
        )
        
        return True
        
    except TelegramError as e:
        logger.error(f"Error sending confirmation to user {user_id}: {e}")
        return False

async def send_payment_error_notification(user_id: int, transaction_id: str):
    """Notificar al usuario sobre error en procesamiento"""
    try:
        error_message = f"""❌ **Error Procesando Pago**

Hemos recibido tu pago pero ocurrió un problema técnico al activar tu suscripción.

🆔 **Referencia:** `{transaction_id}`
⏰ **Reportado:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

**🔧 ¿Qué hacemos ahora?**
• Nuestro equipo técnico fue notificado automáticamente
• Resolveremos este problema en las próximas 2-4 horas
• Recibirás tu acceso tan pronto como se corrija

**📧 ¿Necesitas ayuda urgente?**
Contacta: urgent@pnptv.app
Incluye tu ID de transacción: `{transaction_id}`

¡Gracias por tu paciencia! 🙏

---

❌ **Payment Processing Error**

We received your payment but encountered a technical issue activating your subscription.

🆔 **Reference:** `{transaction_id}`
⏰ **Reported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

**🔧 What happens now?**
• Our technical team was automatically notified
• We'll resolve this within 2-4 hours
• You'll receive access as soon as it's fixed

**📧 Need urgent help?**
Contact: urgent@pnptv.app
Include your transaction ID: `{transaction_id}`

Thank you for your patience! 🙏"""
        
        await bot.send_message(
            chat_id=user_id,
            text=error_message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Failed to send error notification to user {user_id}: {e}")

async def notify_admins_large_payment(user_id: int, plan_name: str, amount: float, transaction_id: str):
    """Notificar administradores sobre pagos grandes"""
    try:
        from bot.config import ADMIN_IDS, CUSTOMER_SERVICE_CHAT_ID
        
        admin_message = f"""💰 **Large Payment Alert**

🎯 **New high-value subscription:**
👤 User ID: `{user_id}`
💎 Plan: {plan_name}
💰 Amount: ${amount:.2f} USD
🆔 Transaction: `{transaction_id}`
📅 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

✅ Payment processed successfully
🎬 User granted access to all channels

Consider following up with VIP support."""
        
        # Notificar a administradores principales
        for admin_id in ADMIN_IDS[:3]:  # Solo primeros 3 admins
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")
        
        # Notificar chat de servicio al cliente si está configurado
        if CUSTOMER_SERVICE_CHAT_ID:
            await bot.send_message(
                chat_id=CUSTOMER_SERVICE_CHAT_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
                
    except Exception as e:
        logger.error(f"Failed to notify admins of large payment: {e}")

async def notify_admins_payment_error(payment_data: Dict, error_msg: str):
    """Notificar administradores sobre errores críticos de pago"""
    try:
        from bot.config import ADMIN_IDS, CUSTOMER_SERVICE_CHAT_ID
        
        # Crear resumen seguro de datos de pago (sin información sensible)
        safe_payment_data = {
            'id': payment_data.get('id', 'Unknown')[:20],
            'status': payment_data.get('status', 'Unknown'),
            'user_id': payment_data.get('metadata', {}).get('user_id', 'Unknown'),
            'plan_id': payment_data.get('metadata', {}).get('plan_id', 'Unknown')
        }
        
        error_message = f"""🚨 **Payment Processing Error**

❌ **Critical payment processing failure**

**Payment Info:**
🆔 Transaction: `{safe_payment_data['id']}`
👤 User ID: `{safe_payment_data['user_id']}`
💎 Plan: {safe_payment_data['plan_id']}
📊 Status: {safe_payment_data['status']}

**Error:**
```
{error_msg[:200]}
```

**Action Required:**
1. Check payment in Bold.co dashboard
2. Manually process if payment successful
3. Contact user if needed
4. Review system logs

📅 **Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC
🔧 **Environment:** {os.getenv('ENVIRONMENT', 'unknown')}"""
        
        # Notificar solo al primer admin para evitar spam
        if ADMIN_IDS:
            await bot.send_message(
                chat_id=ADMIN_IDS[0],
                text=error_message,
                parse_mode='Markdown'
            )
        
        # Notificar chat de servicio al cliente
        if CUSTOMER_SERVICE_CHAT_ID:
            await bot.send_message(
                chat_id=CUSTOMER_SERVICE_CHAT_ID,
                text=error_message,
                parse_mode='Markdown'
            )
                
    except Exception as e:
        logger.error(f"Failed to notify admins of payment error: {e}")

@app.get("/")
async def root():
    """Endpoint de información del webhook"""
    return {
        "service": "PNP TV Enhanced Payment Webhook",
        "status": "active",
        "version": "2.0.1",
        "features": [
            "Signature verification",
            "Rate limiting", 
            "Enhanced validation",
            "Automatic notifications",
            "Error handling"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint mejorado para Railway"""
    try:
        # Verificar conexión a la base de datos
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        
        # Verificar bot
        bot_info = await bot.get_me()
        
        # Verificar configuración crítica
        config_status = {
            "bot_token": bool(BOT_TOKEN),
            "webhook_secret": bool(BOLD_WEBHOOK_SECRET),
            "admin_ids_configured": len(ADMIN_IDS) > 0,
            "signature_required": SECURITY_CONFIG.get("require_webhook_signature", False)
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {
                "status": "connected",
                "total_users": stats.get('total', 0),
                "active_subscriptions": stats.get('active', 0)
            },
            "bot": {
                "status": "connected",
                "username": bot_info.username,
                "id": bot_info.id
            },
            "configuration": config_status,
            "webhook_calls_last_hour": len([
                timestamp for timestamps in webhook_calls.values() 
                for timestamp in timestamps
            ])
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@app.post("/webhook")
async def handle_payment_webhook(
    request: Request, 
    background_tasks: BackgroundTasks
):
    """
    Webhook principal de pagos con seguridad y validación mejorada
    """
    client_ip = request.client.host
    
    # Rate limiting
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Obtener el cuerpo de la request
        body = await request.body()
        
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")
        
        # Verificar firma si está configurada
        signature = request.headers.get('X-Bold-Signature', '') or request.headers.get('X-Signature', '')
        
        if not verify_webhook_signature(body, signature):
            logger.warning(f"Invalid webhook signature from IP: {client_ip}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parsear JSON con validación
        try:
            payment_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook from {client_ip}: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Log del webhook recibido (datos seguros)
        safe_log_data = {
            'payment_id': payment_data.get('id', 'unknown')[:20],
            'status': payment_data.get('status', 'unknown'),
            'ip': client_ip,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Webhook received: {safe_log_data}")
        
        # Verificar estado del pago
        status = payment_data.get('status', '').lower()
        
        if status != 'completed':
            logger.info(f"Webhook ignored - status: {status} from {client_ip}")
            return {
                "status": "ignored", 
                "reason": f"Payment status is {status}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Procesar pago en background para respuesta rápida
        background_tasks.add_task(process_payment_success, payment_data)
        
        # Respuesta inmediata a Bold.co
        return {
            "status": "received",
            "message": "Payment webhook processed successfully",
            "payment_id": str(payment_data.get('id', 'unknown'))[:20],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processing": "background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/webhook/test")
async def test_webhook(request: Request):
    """Endpoint de prueba para el webhook (solo desarrollo)"""
    if os.getenv("ENVIRONMENT") == "production":
        raise HTTPException(status_code=404, detail="Not found")
    
    body = await request.body()
    client_ip = request.client.host
    
    try:
        data = json.loads(body.decode('utf-8'))
        logger.info(f"Test webhook received from {client_ip}: {data}")
        
        # Simular procesamiento
        await asyncio.sleep(0.1)
        
        return {
            "status": "test_received",
            "data": data,
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Test webhook processed successfully"
        }
    except json.JSONDecodeError:
        return {
            "status": "test_received",
            "raw_body": body.decode('utf-8', errors='ignore'),
            "client_ip": client_ip,
            "message": "Raw data received"
        }
    except Exception as e:
        logger.error(f"Error in test webhook: {e}")
        return {
            "status": "test_error",
            "error": str(e),
            "client_ip": client_ip
        }

@app.get("/metrics")
async def get_webhook_metrics():
    """Endpoint de métricas del webhook (protegido)"""
    if os.getenv("ENVIRONMENT") == "production":
        raise HTTPException(status_code=404, detail="Not found")
    
    now = datetime.now().timestamp()
    
    # Calcular métricas de llamadas
    total_calls = sum(len(timestamps) for timestamps in webhook_calls.values())
    recent_calls = sum(
        len([t for t in timestamps if now - t < 3600])  # Última hora
        for timestamps in webhook_calls.values()
    )
    
    unique_ips = len(webhook_calls)
    
    return {
        "webhook_metrics": {
            "total_calls_tracked": total_calls,
            "calls_last_hour": recent_calls,
            "unique_ips": unique_ips,
            "rate_limit_window": RATE_LIMIT_WINDOW,
            "rate_limit_max": RATE_LIMIT_MAX_CALLS
        },
        "security": {
            "signature_verification": bool(BOLD_WEBHOOK_SECRET),
            "signature_required": SECURITY_CONFIG.get("require_webhook_signature", False),
            "cors_enabled": True,
            "rate_limiting": True
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Configuración para Railway
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", WEBHOOK_PORT))
    host = "0.0.0.0"  # Importante para Railway
    
    logger.info(f"Starting enhanced payment webhook server on {host}:{port}")
    logger.info(f"Security features: signature_verification={bool(BOLD_WEBHOOK_SECRET)}, rate_limiting=enabled")
    
    uvicorn.run(
        "payment_webhook:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        loop="asyncio"
    )