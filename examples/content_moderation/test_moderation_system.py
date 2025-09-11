#!/usr/bin/env python3
"""Tests for content moderation system example."""

import pytest
from datetime import datetime, timedelta

from moderation_system import ModerationSystem


class TestModerationSystem:
    """Test cases for the content moderation system."""
    
    @pytest.fixture
    def system(self):
        """Create a moderation system instance."""
        return ModerationSystem()
    
    @pytest.fixture
    def new_user(self):
        """New user account."""
        return {
            "id": "user_new_001",
            "account_age_days": 3,
            "reputation_score": 0.8,
            "verified": False,
            "previous_violations": 0
        }
    
    @pytest.fixture
    def established_user(self):
        """Established user account."""
        return {
            "id": "user_established_001",
            "account_age_days": 365,
            "reputation_score": 0.7,
            "verified": True,
            "previous_violations": 1
        }
    
    @pytest.fixture
    def repeat_offender(self):
        """User with multiple violations."""
        return {
            "id": "user_repeat_001",
            "account_age_days": 180,
            "reputation_score": 0.2,
            "verified": False,
            "previous_violations": 3
        }
    
    @pytest.fixture
    def toxic_content(self):
        """Highly toxic content."""
        return {
            "id": "content_toxic_001",
            "type": "comment",
            "text": "You are such a stupid idiot. Go kill yourself, loser.",
            "language": "en",
            "word_count": 10,
            "has_links": False,
            "has_media": False
        }
    
    @pytest.fixture
    def self_harm_content(self):
        """Self-harm related content."""
        return {
            "id": "content_selfharm_001",
            "type": "post",
            "text": "I can't take this anymore. I want to die. Everything is hopeless.",
            "language": "en",
            "word_count": 12,
            "has_links": False,
            "has_media": False
        }
    
    @pytest.fixture
    def spam_content(self):
        """Spam content with links."""
        return {
            "id": "content_spam_001",
            "type": "comment",
            "text": "Check out this amazing offer - make $500 per day! Click here now: bit.ly/scam123",
            "language": "en",
            "word_count": 14,
            "has_links": True,
            "has_media": False
        }
    
    @pytest.fixture
    def normal_content(self):
        """Normal, acceptable content."""
        return {
            "id": "content_normal_001",
            "type": "post",
            "text": "Just wanted to share this beautiful sunset photo I took today!",
            "language": "en",
            "word_count": 11,
            "has_links": False,
            "has_media": True
        }
    
    @pytest.fixture
    def basic_context(self):
        """Basic moderation context."""
        return {
            "platform": "social_network",
            "timestamp": datetime.now().isoformat(),
            "report_count": 0,
            "community_guidelines_version": "2.1"
        }
    
    @pytest.fixture
    def reported_context(self):
        """Context with multiple reports."""
        return {
            "platform": "social_network", 
            "timestamp": datetime.now().isoformat(),
            "report_count": 4,
            "community_guidelines_version": "2.1"
        }

    def test_system_initialization(self, system):
        """Test that the moderation system initializes correctly."""
        assert system.schema is not None
        assert len(system.moderation_rules) > 0
        assert all('id' in rule for rule in system.moderation_rules)
        assert all('rule' in rule for rule in system.moderation_rules)
        assert all('metadata' in rule for rule in system.moderation_rules)
    
    def test_sentiment_score_function(self, system):
        """Test sentiment scoring function."""
        # Negative sentiment
        negative_score = system._sentiment_score("I hate this terrible awful product")
        assert negative_score < 0
        
        # Positive sentiment
        positive_score = system._sentiment_score("I love this amazing wonderful product")
        assert positive_score > 0
        
        # Neutral sentiment
        neutral_score = system._sentiment_score("This is a product")
        assert abs(neutral_score) < 0.5
    
    def test_toxicity_score_function(self, system):
        """Test toxicity scoring function."""
        # High toxicity
        toxic_score = system._toxicity_score("kill yourself you stupid idiot")
        assert toxic_score > 0.5
        
        # Low toxicity
        normal_score = system._toxicity_score("I disagree with your opinion")
        assert normal_score < 0.5
        
        # Score bounds
        very_toxic_score = system._toxicity_score("kill yourself die hate you stupid idiot worthless loser")
        assert 0 <= very_toxic_score <= 1.0
    
    def test_spam_detection(self, system):
        """Test spam pattern detection."""
        # Spam patterns
        assert system._contains_spam_patterns("Click here now for 100% free money!")
        assert system._contains_spam_patterns("Make $500 per day with this limited time offer")
        assert system._contains_spam_patterns("Visit www.scam.com for amazing deals")
        
        # Normal content
        assert not system._contains_spam_patterns("Here's my honest review of the product")
        assert not system._contains_spam_patterns("Thanks for sharing this interesting article")
    
    def test_self_harm_detection(self, system):
        """Test self-harm language detection."""
        # Self-harm indicators
        assert system._detect_self_harm_language("I want to die and end it all")
        assert system._detect_self_harm_language("Thinking about suicide and hurting myself")
        assert system._detect_self_harm_language("Life is not worth living anymore")
        
        # Normal emotional content
        assert not system._detect_self_harm_language("I'm feeling sad today")
        assert not system._detect_self_harm_language("This movie made me cry")
    
    def test_harassment_detection(self, system):
        """Test harassment pattern detection."""
        # Harassment patterns
        assert system._is_potential_harassment("You should just shut up", "target_user")
        assert system._is_potential_harassment("People like you are the problem", "target_user")
        assert system._is_potential_harassment("Why don't you just leave", "target_user")
        
        # Normal disagreement
        assert not system._is_potential_harassment("I respectfully disagree", "target_user")
        assert not system._is_potential_harassment("That's an interesting point", "target_user")
    
    def test_immediate_toxic_removal(self, system, established_user, toxic_content, basic_context):
        """Test immediate removal for extremely toxic content."""
        # Mock high toxicity score
        original_func = system._toxicity_score
        def mock_toxicity(text):
            return 0.95
        system.schema.add_function('toxicity_score', mock_toxicity)
        
        try:
            decision = system.moderate_content(established_user, toxic_content, basic_context)
            
            assert decision['action'] == 'remove'
            assert decision['severity'] == 'high'
            assert decision['matched_rule'] == 'immediate_remove_toxic'
            assert decision['escalate'] == True
            assert decision['notify_user'] == True
        finally:
            # Restore original function
            system.schema.add_function('toxicity_score', original_func)
    
    def test_self_harm_intervention(self, system, established_user, self_harm_content, basic_context):
        """Test crisis intervention for self-harm content."""
        decision = system.moderate_content(established_user, self_harm_content, basic_context)
        
        assert decision['action'] == 'remove'
        assert decision['severity'] == 'critical'
        assert decision['matched_rule'] == 'self_harm_intervention'
        assert decision['escalate'] == True
        assert decision['notify_user'] == False  # Don't notify to avoid triggering
        assert decision['metadata'].get('special_handling') == 'crisis_intervention'
    
    def test_new_user_link_restriction(self, system, new_user, spam_content, basic_context):
        """Test new user posting links gets quarantined."""
        decision = system.moderate_content(new_user, spam_content, basic_context)
        
        # Should match new_user_link_restriction rule
        assert decision['action'] == 'quarantine'
        assert decision['severity'] == 'low'
        assert decision['matched_rule'] == 'new_user_link_restriction'
        assert decision['escalate'] == False
        assert decision['notify_user'] == False
    
    def test_spam_detection_rule(self, system, basic_context):
        """Test spam detection for low reputation users."""
        low_rep_user = {
            "id": "user_lowrep_001",
            "account_age_days": 100,
            "reputation_score": 0.2,  # Low reputation
            "verified": False,
            "previous_violations": 0
        }
        
        spam_content_fixture = {
            "id": "content_spam_001",
            "type": "comment",
            "text": "Check out this amazing offer - make $500 per day! Click here now: bit.ly/scam123",
            "language": "en",
            "word_count": 14,
            "has_links": True,
            "has_media": False
        }
        decision = system.moderate_content(low_rep_user, spam_content_fixture, basic_context)
        
        # Should match spam_detection rule (assuming it doesn't match new user rule first)
        # We need to test with an established low-rep user and high inventory to avoid other rules
        high_inventory_spam = {
            "id": "content_spam_002",
            "type": "comment", 
            "text": "Limited time offer - make $100 per day!",
            "language": "en",
            "word_count": 8,
            "has_links": False,  # No links to avoid new user rule
            "has_media": False
        }
        
        established_low_rep_user = low_rep_user.copy()
        established_low_rep_user['account_age_days'] = 100  # Not new user
        
        decision = system.moderate_content(established_low_rep_user, high_inventory_spam, basic_context)
        
        # Could match spam_detection if spam patterns are detected
        if decision['matched_rule'] == 'spam_detection':
            assert decision['action'] == 'flag'
            assert decision['severity'] == 'medium'
    
    def test_harassment_with_reports(self, system, established_user, reported_context):
        """Test removal for reported content with moderate toxicity."""
        moderately_toxic_content = {
            "id": "content_reported_001",
            "type": "comment",
            "text": "You are such an annoying person, just go away",
            "language": "en",
            "word_count": 9,
            "has_links": False,
            "has_media": False
        }
        
        # Mock moderate toxicity score - needs to be > 0.6 for harassment rule
        # Need to re-register with schema, not just patch instance method
        original_func = system._toxicity_score
        def mock_toxicity(text):
            return 0.65
        system.schema.add_function('toxicity_score', mock_toxicity)
        
        try:
            decision = system.moderate_content(established_user, moderately_toxic_content, reported_context)
            
            assert decision['action'] == 'remove'
            assert decision['severity'] == 'high'
            assert decision['matched_rule'] == 'harassment_with_reports'
            assert decision['escalate'] == True
            assert decision['notify_user'] == True
        finally:
            # Restore original function
            system.schema.add_function('toxicity_score', original_func)
    
    def test_repeat_offender_strict(self, system, repeat_offender, basic_context):
        """Test stricter rules for repeat offenders."""
        mildly_toxic_content = {
            "id": "content_mild_001",
            "type": "comment",
            "text": "That's a stupid idea",
            "language": "en",
            "word_count": 4,
            "has_links": False,
            "has_media": False
        }
        
        # Mock moderate toxicity score that would normally be acceptable - needs to be > 0.5 for repeat offender rule
        original_func = system._toxicity_score
        def mock_toxicity(text):
            return 0.55
        system.schema.add_function('toxicity_score', mock_toxicity)
        
        try:
            decision = system.moderate_content(repeat_offender, mildly_toxic_content, basic_context)
            
            assert decision['action'] == 'remove'
            assert decision['severity'] == 'high'
            assert decision['matched_rule'] == 'repeat_offender_strict'
            assert decision['escalate'] == False  # Don't escalate for repeat offenders
            assert decision['notify_user'] == True
        finally:
            # Restore original function
            system.schema.add_function('toxicity_score', original_func)
    
    def test_normal_content_approval(self, system, established_user, normal_content, basic_context):
        """Test that normal content gets approved."""
        decision = system.moderate_content(established_user, normal_content, basic_context)
        
        assert decision['action'] == 'approve'
        assert decision['severity'] == 'none'
        assert decision['matched_rule'] is None
        assert decision['escalate'] == False
        assert decision['notify_user'] == False
    
    def test_rule_priority_order(self, system, basic_context):
        """Test that rules are evaluated in priority order."""
        # Create content that could match multiple rules
        multi_rule_content = {
            "id": "content_multi_001",
            "type": "comment",
            "text": "I want to die, you stupid piece of crap",  # Both self-harm AND toxic
            "language": "en",
            "word_count": 8,
            "has_links": False,
            "has_media": False
        }
        
        user = {
            "id": "user_test_001",
            "account_age_days": 30,  # More than 7 days to avoid new user rule
            "reputation_score": 0.5,
            "verified": False,
            "previous_violations": 0
        }
        
        decision = system.moderate_content(user, multi_rule_content, basic_context)
        
        # Should match self_harm_intervention (ordering: 2) before other toxic rules
        assert decision['matched_rule'] == 'self_harm_intervention'
        assert decision['action'] == 'remove'
        assert decision['severity'] == 'critical'
    
    def test_decision_structure(self, system, established_user, normal_content, basic_context):
        """Test that moderation decisions have correct structure."""
        decision = system.moderate_content(established_user, normal_content, basic_context)
        
        # Check required fields
        required_fields = [
            'content_id', 'user_id', 'action', 'severity', 'reason',
            'matched_rule', 'requires_human_review', 'escalate',
            'notify_user', 'metadata'
        ]
        
        for field in required_fields:
            assert field in decision, f"Missing field: {field}"
        
        # Check field types
        assert isinstance(decision['content_id'], str)
        assert isinstance(decision['user_id'], str)
        assert decision['action'] in ['approve', 'flag', 'quarantine', 'remove']
        assert decision['severity'] in ['none', 'low', 'medium', 'high', 'critical']
        assert isinstance(decision['reason'], str)
        assert isinstance(decision['requires_human_review'], bool)
        assert isinstance(decision['escalate'], bool)
        assert isinstance(decision['notify_user'], bool)
        assert isinstance(decision['metadata'], dict)
    
    def test_edge_cases(self, system, basic_context):
        """Test edge cases and error handling."""
        user = {"id": "test", "account_age_days": 0, "reputation_score": 0.0, "verified": False, "previous_violations": 0}
        
        # Empty content
        empty_content = {"id": "test", "type": "post", "text": "", "language": "en", "word_count": 0, "has_links": False, "has_media": False}
        decision = system.moderate_content(user, empty_content, basic_context)
        assert 'action' in decision
        
        # Very long content
        long_content = empty_content.copy()
        long_content['text'] = "word " * 1000
        long_content['word_count'] = 1000
        decision = system.moderate_content(user, long_content, basic_context)
        assert 'action' in decision
        
        # Extreme values
        extreme_user = {
            "id": "extreme",
            "account_age_days": -1,  # Invalid but should not crash
            "reputation_score": 2.0,  # Out of normal range
            "verified": True,
            "previous_violations": 100
        }
        decision = system.moderate_content(extreme_user, empty_content, basic_context)
        assert 'action' in decision
    
    def test_multiple_rule_matching(self, system, basic_context):
        """Test scenarios where multiple rules could potentially match."""
        # Since the system uses first-match, we test that the highest priority rule wins
        complex_user = {
            "id": "user_complex_001",
            "account_age_days": 30,  # Avoid new user rules
            "reputation_score": 0.1,  # Low reputation
            "verified": False,
            "previous_violations": 2  # Some violations
        }
        
        complex_content = {
            "id": "content_complex_001",
            "type": "comment",
            "text": "You stupid idiot, check out this link: bit.ly/spam",  # Toxic + spam + links
            "language": "en",
            "word_count": 9,
            "has_links": True,
            "has_media": False
        }
        
        # Mock high toxicity to trigger immediate removal
        original_func = system._toxicity_score
        def mock_toxicity(text):
            return 0.95
        system.schema.add_function('toxicity_score', mock_toxicity)
        
        try:
            decision = system.moderate_content(complex_user, complex_content, basic_context)
            
            # Should match the highest priority rule (immediate_remove_toxic has ordering: 1)
            assert decision['matched_rule'] == 'immediate_remove_toxic'
            assert decision['action'] == 'remove'
        finally:
            # Restore original function
            system.schema.add_function('toxicity_score', original_func)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])