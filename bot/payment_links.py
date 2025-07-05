# -*- coding: utf-8 -*-
import hashlib
import time
import json
from typing import Dict, Optional
from bot.config import generate_bold_link, PLAN_LINK_IDS, PLANS

class PaymentLinkGenerator:
    """Generate dynamic payment links with BOLD system"""
    
    def __init__(self):
        self.active_links = {}  # Store active payment links
    
    def generate_payment_link(self, user_id: int, plan_name: str) -> str:
        """Generate BOLD payment link with user and plan metadata."""

        # Get link ID for plan
        link_id = PLAN_LINK_IDS.get(plan_name)
        if not link_id:
            raise ValueError(f"No link ID found for plan: {plan_name}")

        # Determine plan identifier used in PLANS
        plan_id = None
        for p_id, info in PLANS.items():
            if info["name"] == plan_name:
                plan_id = p_id
                break
        if plan_id is None:
            raise ValueError(f"No plan identifier found for plan: {plan_name}")
        
        # Create unique transaction ID
        timestamp = int(time.time())
        unique_string = f"{user_id}_{plan_name}_{timestamp}"
        transaction_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        
        # Generate BOLD URL with metadata
        payment_url = generate_bold_link(link_id, user_id, plan_id)
        
        # Store link for verification
        self.active_links[transaction_id] = {
            "user_id": user_id,
            "plan_name": plan_name,
            "plan_id": plan_id,
            "link_id": link_id,
            "created_at": timestamp,
            "status": "pending",
            "payment_url": payment_url
        }
        
        return payment_url
    
    def verify_payment_link(self, transaction_id: str) -> Optional[Dict]:
        """Verify if payment link exists and is valid"""
        return self.active_links.get(transaction_id)
    
    def mark_payment_completed(self, user_id: int, plan_name: str) -> bool:
        """Mark payment as completed by user_id and plan"""
        for tx_id, link_data in self.active_links.items():
            if (link_data["user_id"] == user_id and 
                link_data["plan_name"] == plan_name and 
                link_data["status"] == "pending"):
                link_data["status"] = "completed"
                link_data["completed_at"] = int(time.time())
                return True
        return False
    
    def get_user_payments(self, user_id: int) -> list:
        """Get all payments for a user"""
        return [link for link in self.active_links.values() 
                if link["user_id"] == user_id]

# Global instance
payment_generator = PaymentLinkGenerator()

