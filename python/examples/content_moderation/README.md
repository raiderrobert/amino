# Content Moderation System

This example demonstrates how to build an AI-powered content moderation system using Amino, where safety teams can rapidly respond to emerging threats by updating moderation rules without requiring code deployments.

## Use Case

A social media platform needs to:
- Automatically detect and handle toxic, harmful, or inappropriate content
- Adapt quickly to new forms of abuse and harassment
- Balance automation with human review for edge cases
- Allow safety teams to fine-tune rules based on community feedback

## Key Features

- **Multi-Signal Analysis**: Combines ML scores, user reputation, and community reports
- **Priority-Based Rules**: Critical safety rules (self-harm) take precedence
- **Graduated Responses**: Actions range from flagging to immediate removal
- **Human Escalation**: Complex cases are escalated for manual review

## Schema

The `schema.amino` file defines:
- **User**: account age, reputation, violation history
- **Content**: text, metadata, links, media
- **Context**: platform info, reports, timestamps
- **ML Functions**: sentiment, toxicity, spam detection

## Sample Rules

```python
# Immediate removal for extremely toxic content
"toxicity_score(content.text) > 0.9"

# Crisis intervention for self-harm language  
"detect_self_harm_language(content.text)"

# New users posting links need review
"user.account_age_days < 7 and content.has_links"

# Multiple reports + moderate toxicity = remove
"context.report_count >= 3 and toxicity_score(content.text) > 0.6"

# Stricter rules for repeat offenders
"user.previous_violations >= 2 and toxicity_score(content.text) > 0.5"
```

## Action Types

- **Approve**: Content passes all checks
- **Flag**: Requires human review but stays live
- **Quarantine**: Hidden pending review
- **Remove**: Immediately deleted, user notified

## Running the Example

```bash
cd examples/content_moderation
python moderation_system.py
```

## Expected Output

The demo shows various content scenarios:
- Spam links from new users → Quarantined
- Self-harm language → Immediate removal + crisis intervention
- Toxic harassment → Removed with escalation
- Normal content → Approved

## Safety Benefits

1. **Rapid Response**: New abuse patterns can be blocked in minutes
2. **Consistent Enforcement**: Rules apply uniformly across all content
3. **Audit Trail**: Every moderation decision is traceable and explainable
4. **Graduated Enforcement**: Appropriate response based on severity and context
5. **Human Oversight**: Critical cases still get human review