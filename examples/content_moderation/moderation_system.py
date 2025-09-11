#!/usr/bin/env python3
"""
Content Moderation System Example

This example demonstrates how to use Amino to build a flexible content moderation
system where safety teams can rapidly respond to new threats by updating rules
without requiring code deployments.
"""

import amino
import re
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta


class ModerationSystem:
    """AI-powered content moderation with flexible rule engine."""
    
    def __init__(self):
        # Load the schema
        with open('examples/content_moderation/schema.amino', 'r') as f:
            schema_content = f.read()
        
        self.schema = amino.Schema(schema_content)
        
        # Register ML and analysis functions
        self.schema.add_function('sentiment_score', self._sentiment_score)
        self.schema.add_function('toxicity_score', self._toxicity_score)
        self.schema.add_function('contains_spam_patterns', self._contains_spam_patterns)
        self.schema.add_function('contains_banned_words', self._contains_banned_words)
        self.schema.add_function('is_potential_harassment', self._is_potential_harassment)
        self.schema.add_function('detect_self_harm_language', self._detect_self_harm_language)
        
        # Safety team defined moderation rules
        self.moderation_rules = [
            {
                "id": "immediate_remove_toxic",
                "rule": "toxicity_score(content.text) > 0.9",
                "ordering": 1,
                "metadata": {
                    "action": "remove",
                    "severity": "high",
                    "reason": "Extremely toxic content detected",
                    "notify_user": True,
                    "escalate": True
                }
            },
            {
                "id": "self_harm_intervention",
                "rule": "detect_self_harm_language(content.text)",
                "ordering": 2,
                "metadata": {
                    "action": "remove",
                    "severity": "critical",
                    "reason": "Self-harm language detected - intervention required",
                    "notify_user": False,
                    "escalate": True,
                    "special_handling": "crisis_intervention"
                }
            },
            {
                "id": "new_user_link_restriction",
                "rule": "user.account_age_days < 7 and content.has_links",
                "ordering": 3,
                "metadata": {
                    "action": "quarantine",
                    "severity": "low",
                    "reason": "New user posting links - requires review",
                    "notify_user": False,
                    "escalate": False
                }
            },
            {
                "id": "spam_detection",
                "rule": "contains_spam_patterns(content.text) and user.reputation_score < 0.3",
                "ordering": 4,
                "metadata": {
                    "action": "flag",
                    "severity": "medium", 
                    "reason": "Potential spam content",
                    "notify_user": False,
                    "escalate": False
                }
            },
            {
                "id": "harassment_with_reports",
                "rule": "context.report_count >= 3 and toxicity_score(content.text) > 0.6",
                "ordering": 5,
                "metadata": {
                    "action": "remove",
                    "severity": "high",
                    "reason": "Multiple reports + toxic content",
                    "notify_user": True,
                    "escalate": True
                }
            },
            {
                "id": "repeat_offender_strict",
                "rule": "user.previous_violations >= 2 and toxicity_score(content.text) > 0.5",
                "ordering": 6,
                "metadata": {
                    "action": "remove",
                    "severity": "high",
                    "reason": "Repeat offender with toxic content",
                    "notify_user": True,
                    "escalate": False
                }
            },
            {
                "id": "banned_words_filter",
                "rule": "contains_banned_words(content.text)",
                "ordering": 7,
                "metadata": {
                    "action": "flag",
                    "severity": "medium",
                    "reason": "Contains prohibited language",
                    "notify_user": True,
                    "escalate": False
                }
            }
        ]
    
    def _sentiment_score(self, text: str) -> float:
        """Simulate sentiment analysis (returns -1.0 to 1.0)."""
        # Mock implementation - in reality, would call ML service
        negative_words = ['hate', 'terrible', 'awful', 'stupid', 'worst', 'horrible']
        positive_words = ['love', 'great', 'awesome', 'amazing', 'best', 'wonderful']
        
        text_lower = text.lower()
        negative_count = sum(1 for word in negative_words if word in text_lower)
        positive_count = sum(1 for word in positive_words if word in text_lower)
        
        if negative_count > positive_count:
            return -0.3 - (negative_count * 0.1)
        elif positive_count > negative_count:
            return 0.3 + (positive_count * 0.1)
        return 0.0
    
    def _toxicity_score(self, text: str) -> float:
        """Simulate toxicity detection (returns 0.0 to 1.0)."""
        # Mock implementation - in reality, would call ML service like Perspective API
        toxic_indicators = [
            'kill yourself', 'kys', 'die', 'hate you', 'stupid idiot',
            'go to hell', 'piece of crap', 'worthless', 'loser'
        ]
        
        text_lower = text.lower()
        score = 0.0
        
        for indicator in toxic_indicators:
            if indicator in text_lower:
                score += 0.3
        
        # Add some randomness to simulate ML uncertainty
        score += random.uniform(0, 0.2)
        return min(score, 1.0)
    
    def _contains_spam_patterns(self, text: str) -> bool:
        """Detect common spam patterns."""
        spam_patterns = [
            r'click here now',
            r'limited time offer',
            r'make \$\d+ per day',
            r'100% free',
            r'www\.[a-z]+\.com',
            r'bit\.ly/',
        ]
        
        text_lower = text.lower()
        for pattern in spam_patterns:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _contains_banned_words(self, text: str) -> bool:
        """Check against banned words list."""
        # Simplified banned words (in practice, this would be more comprehensive)
        banned_words = [
            'badword1', 'badword2', 'offensive_term'  # Placeholder terms
        ]
        
        text_lower = text.lower()
        return any(word in text_lower for word in banned_words)
    
    def _is_potential_harassment(self, text: str, target_user: str) -> bool:
        """Detect targeted harassment."""
        harassment_indicators = [
            'you should', 'you are such a', 'people like you',
            'why don\'t you', 'shut up'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in harassment_indicators)
    
    def _detect_self_harm_language(self, text: str) -> bool:
        """Detect self-harm or suicide-related content."""
        self_harm_indicators = [
            'want to die', 'kill myself', 'end it all', 'not worth living',
            'suicide', 'hurt myself', 'cut myself'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self_harm_indicators)
    
    def moderate_content(self, user_data: Dict[str, Any], content_data: Dict[str, Any],
                        context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate content against moderation rules."""
        
        # Combine all data for rule evaluation
        moderation_data = {
            "user": user_data,
            "content": content_data,
            "context": context_data
        }
        
        # Compile rules for evaluation (first match wins - highest priority)
        compiled_rules = self.schema.compile(
            self.moderation_rules,
            match={"option": "first", "key": "ordering", "ordering": "asc"}
        )
        
        # Evaluate rules against the content
        results = compiled_rules.eval([{"id": "moderation_decision", **moderation_data}])
        
        decision = {
            "content_id": content_data["id"],
            "user_id": user_data["id"],
            "action": "approve",  # Default action
            "severity": "none",
            "reason": "Content passed all moderation checks",
            "matched_rule": None,
            "requires_human_review": False,
            "escalate": False,
            "notify_user": False,
            "metadata": {}
        }
        
        if results and results[0].results:
            # Get the first matching rule (highest priority)
            matched_rule_id = results[0].results[0]
            
            # Find the rule metadata
            for rule in self.moderation_rules:
                if rule["id"] == matched_rule_id:
                    metadata = rule["metadata"]
                    decision.update({
                        "action": metadata["action"],
                        "severity": metadata["severity"],
                        "reason": metadata["reason"],
                        "matched_rule": matched_rule_id,
                        "requires_human_review": metadata.get("escalate", False),
                        "escalate": metadata.get("escalate", False),
                        "notify_user": metadata.get("notify_user", False),
                        "metadata": metadata
                    })
                    break
        
        return decision


def main():
    """Demo the content moderation system."""
    system = ModerationSystem()
    
    # Sample user data
    users = [
        {
            "id": "user_001",
            "account_age_days": 2,
            "reputation_score": 0.8,
            "verified": False,
            "previous_violations": 0
        },
        {
            "id": "user_002",
            "account_age_days": 365,
            "reputation_score": 0.2,
            "verified": True,
            "previous_violations": 3
        }
    ]
    
    # Sample content to moderate
    content_samples = [
        {
            "id": "content_001",
            "type": "comment",
            "text": "Check out this amazing offer - make $500 per day! Click here now: bit.ly/scam123",
            "language": "en",
            "word_count": 14,
            "has_links": True,
            "has_media": False
        },
        {
            "id": "content_002",
            "type": "post",
            "text": "I can't take this anymore. I want to die. Everything is hopeless.",
            "language": "en", 
            "word_count": 12,
            "has_links": False,
            "has_media": False
        },
        {
            "id": "content_003",
            "type": "comment",
            "text": "You are such a stupid idiot. Go kill yourself, loser.",
            "language": "en",
            "word_count": 10,
            "has_links": False,
            "has_media": False
        },
        {
            "id": "content_004",
            "type": "post",
            "text": "Just wanted to share this beautiful sunset photo I took today!",
            "language": "en",
            "word_count": 11,
            "has_links": False,
            "has_media": True
        }
    ]
    
    context = {
        "platform": "social_network",
        "timestamp": datetime.now().isoformat(),
        "report_count": 0,
        "community_guidelines_version": "2.1"
    }
    
    print("🛡️ Content Moderation System Demo")
    print("=" * 50)
    
    for i, user in enumerate(users):
        print(f"\n👤 User {i+1}: {user['account_age_days']} days old, "
              f"{user['previous_violations']} violations")
        
        for j, content in enumerate(content_samples):
            print(f"\n📝 Content {j+1}: \"{content['text'][:50]}{'...' if len(content['text']) > 50 else ''}\"")
            
            # Adjust context for some examples
            test_context = context.copy()
            if j == 2:  # Toxic content gets reports
                test_context["report_count"] = 4
            
            decision = system.moderate_content(user, content, test_context)
            
            action_emoji = {
                "approve": "✅",
                "flag": "🏴",
                "quarantine": "⚠️", 
                "remove": "❌"
            }.get(decision["action"], "❓")
            
            print(f"   {action_emoji} Action: {decision['action'].upper()}")
            print(f"   📊 Severity: {decision['severity']}")
            print(f"   💭 Reason: {decision['reason']}")
            
            if decision["matched_rule"]:
                print(f"   🎯 Rule: {decision['matched_rule']}")
                
            if decision["escalate"]:
                print(f"   🚨 Requires human review!")


if __name__ == "__main__":
    main()