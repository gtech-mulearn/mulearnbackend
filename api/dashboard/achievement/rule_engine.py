"""
Achievement Rule Engine

Properties:
- Stateless: No side effects
- Deterministic: Same input = same output
- Versioned: Rules are immutable once created

Usage:
    from api.dashboard.achievement.rule_engine import RuleEvaluator
    evaluator = RuleEvaluator(user_id="...")
    eligible = evaluator.get_eligible_achievements()
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of rule evaluation"""
    eligible: bool
    achievement_id: str
    achievement_name: str
    rule_version: int
    reason: str
    progress: Dict[str, Any] = field(default_factory=dict)
    claimed: bool = False  # True when the user has already claimed this achievement


class RuleEvaluator:
    """
    Evaluates achievement rules against user state.
    Stateless - fetches required data and evaluates.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._cache = {}  # Cache user data within single evaluation

    def get_eligible_achievements(self) -> List[EligibilityResult]:
        """
        Get all achievements the user is eligible to claim.
        Only returns achievements not already claimed.
        """
        from db.achievement import AchievementRule, UserAchievementsLog

        results = []

        # Get already claimed achievements
        claimed_ids = set(
            UserAchievementsLog.objects.filter(user_id=self.user_id).values_list(
                "achievement_id", flat=True
            )
        )

        # Get all active rules
        active_rules = AchievementRule.objects.filter(is_active=True).select_related(
            "achievement"
        )

        for rule in active_rules:
            # Skip if already claimed
            if str(rule.achievement_id) in claimed_ids:
                continue

            result = self.evaluate_rule(rule)
            if result.eligible:
                results.append(result)

        return results

    def get_all_progress(self) -> List[EligibilityResult]:
        """
        Get progress towards all achievements (claimed or not).
        Returns all results, not just eligible ones.
        """
        from db.achievement import AchievementRule, UserAchievementsLog

        results = []

        # Get already claimed achievements
        claimed_ids = set(
            UserAchievementsLog.objects.filter(user_id=self.user_id).values_list(
                "achievement_id", flat=True
            )
        )

        # Get all active rules
        active_rules = AchievementRule.objects.filter(is_active=True).select_related(
            "achievement"
        )

        for rule in active_rules:
            result = self.evaluate_rule(rule)
            # Mark if already claimed without overriding the rule-based eligibility
            if str(rule.achievement_id) in claimed_ids:
                result.claimed = True
                result.reason = "Already claimed"
            results.append(result)

        return results

    def evaluate_rule(self, rule) -> EligibilityResult:
        """Evaluate a single rule"""
        evaluator = self._get_evaluator(rule.rule_type)
        return evaluator(rule)

    def evaluate_achievement(self, achievement_id: str) -> Optional[EligibilityResult]:
        """Evaluate eligibility for a specific achievement"""
        from db.achievement import AchievementRule

        rule = (
            AchievementRule.objects.filter(
                achievement_id=achievement_id, is_active=True
            )
            .select_related("achievement")
            .order_by("-version")
            .first()
        )

        if not rule:
            return None

        return self.evaluate_rule(rule)

    def _get_evaluator(self, rule_type: str):
        """Get evaluator function for rule type"""
        evaluators = {
            "ig_karma": self._evaluate_ig_karma,
            "skill": self._evaluate_skill,
            "streak": self._evaluate_streak,
            "milestone": self._evaluate_milestone,
            "event": self._evaluate_event,
            "task_completion": self._evaluate_task_completion,
        }
        return evaluators.get(rule_type, self._evaluate_unknown)

    def _evaluate_task_completion(self, rule) -> EligibilityResult:
        """Evaluate task completion rule"""
        conditions = rule.conditions
        task_hashtag = conditions.get("task_hashtag")
        
        # Check if user has completed the task
        from db.task import KarmaActivityLog
        
        has_completed = KarmaActivityLog.objects.filter(
            user_id=self.user_id,
            task__hashtag=task_hashtag,
            appraiser_approved=True
        ).exists()

        return EligibilityResult(
            eligible=has_completed,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name,
            rule_version=rule.version,
            reason=f"Task Completion: {task_hashtag}",
            progress={
                "current": 1 if has_completed else 0,
                "required": 1,
                "percentage": 100 if has_completed else 0,
                "task_hashtag": task_hashtag,
            },
        )

    def _evaluate_ig_karma(self, rule) -> EligibilityResult:
        """Evaluate IG karma threshold rule"""
        conditions = rule.conditions
        ig_id = conditions.get("ig_id")
        required_karma = conditions.get("required_karma", 0)

        user_ig_karma = self._get_user_ig_karma(ig_id)
        current_karma = user_ig_karma.total_karma if user_ig_karma else 0

        percentage = (
            min(100, int(current_karma / required_karma * 100))
            if required_karma
            else 100
        )

        return EligibilityResult(
            eligible=current_karma >= required_karma,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name,
            rule_version=rule.version,
            reason=f"IG Karma: {current_karma}/{required_karma}",
            progress={
                "current": current_karma,
                "required": required_karma,
                "percentage": percentage,
                "ig_id": ig_id,
            },
        )

    def _evaluate_skill(self, rule) -> EligibilityResult:
        """Evaluate skill task count rule"""
        conditions = rule.conditions
        skill_id = conditions.get("skill_id")
        required_tasks = conditions.get("required_tasks", 0)

        progress = self._get_skill_progress(skill_id)
        current_tasks = progress.completed_task_count if progress else 0

        percentage = (
            min(100, int(current_tasks / required_tasks * 100))
            if required_tasks
            else 100
        )

        return EligibilityResult(
            eligible=current_tasks >= required_tasks,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name,
            rule_version=rule.version,
            reason=f"Skill Tasks: {current_tasks}/{required_tasks}",
            progress={
                "current": current_tasks,
                "required": required_tasks,
                "percentage": percentage,
                "skill_id": skill_id,
            },
        )

    def _evaluate_streak(self, rule) -> EligibilityResult:
        """Evaluate streak rule"""
        conditions = rule.conditions
        streak_type = conditions.get("streak_type", "daily_task")
        required_streak = conditions.get("required_streak", 0)

        streak = self._get_user_streak(streak_type)
        current_streak = streak.current_streak if streak else 0

        percentage = (
            min(100, int(current_streak / required_streak * 100))
            if required_streak
            else 100
        )

        return EligibilityResult(
            eligible=current_streak >= required_streak,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name,
            rule_version=rule.version,
            reason=f"Streak: {current_streak}/{required_streak} days",
            progress={
                "current": current_streak,
                "required": required_streak,
                "percentage": percentage,
                "streak_type": streak_type,
            },
        )

    def _evaluate_milestone(self, rule) -> EligibilityResult:
        """Evaluate total milestone rule (total karma, total tasks, etc.)"""
        conditions = rule.conditions
        milestone_type = conditions.get("milestone_type", "total_karma")
        required_value = conditions.get("required_value", 0)

        current_value = 0
        if milestone_type == "total_karma":
            wallet = self._get_wallet()
            current_value = wallet.karma if wallet else 0
        elif milestone_type == "total_tasks":
            current_value = self._get_total_task_count()

        percentage = (
            min(100, int(current_value / required_value * 100))
            if required_value
            else 100
        )

        return EligibilityResult(
            eligible=current_value >= required_value,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name,
            rule_version=rule.version,
            reason=f"{milestone_type}: {current_value}/{required_value}",
            progress={
                "current": current_value,
                "required": required_value,
                "percentage": percentage,
                "milestone_type": milestone_type,
            },
        )

    def _evaluate_event(self, rule) -> EligibilityResult:
        """Evaluate event attendance rule"""
        conditions = rule.conditions
        event_name = conditions.get("event_name")
        required_attendance = conditions.get("required_attendance", 1)

        # Count attendance from karma_activity_log
        from db.task import KarmaActivityLog

        attendance = KarmaActivityLog.objects.filter(
            user_id=self.user_id, task__event=event_name, appraiser_approved=True
        ).count()

        percentage = (
            min(100, int(attendance / required_attendance * 100))
            if required_attendance
            else 100
        )

        return EligibilityResult(
            eligible=attendance >= required_attendance,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name,
            rule_version=rule.version,
            reason=f"Event Attendance: {attendance}/{required_attendance}",
            progress={
                "current": attendance,
                "required": required_attendance,
                "percentage": percentage,
                "event_name": event_name,
            },
        )

    def _evaluate_unknown(self, rule) -> EligibilityResult:
        """Handle unknown rule types"""
        return EligibilityResult(
            eligible=False,
            achievement_id=str(rule.achievement_id),
            achievement_name=rule.achievement.name if rule.achievement else "Unknown",
            rule_version=rule.version,
            reason=f"Unknown rule type: {rule.rule_type}",
        )

    # ========================================================================
    # Data fetching methods (cached within single evaluation)
    # ========================================================================

    def _get_user_ig_karma(self, ig_id: str):
        """Get user's karma for a specific IG"""
        from db.achievement import UserIgKarma

        cache_key = f"ig_karma_{ig_id}"
        if cache_key not in self._cache:
            self._cache[cache_key] = UserIgKarma.objects.filter(
                user_id=self.user_id, ig_id=ig_id
            ).first()
        return self._cache[cache_key]

    def _get_skill_progress(self, skill_id: str):
        """Get user's progress for a specific skill"""
        from db.achievement import UserSkillProgress

        cache_key = f"skill_{skill_id}"
        if cache_key not in self._cache:
            self._cache[cache_key] = UserSkillProgress.objects.filter(
                user_id=self.user_id, skill_id=skill_id
            ).first()
        return self._cache[cache_key]

    def _get_user_streak(self, streak_type: str):
        """Get user's streak of a specific type"""
        from db.achievement import UserStreak

        cache_key = f"streak_{streak_type}"
        if cache_key not in self._cache:
            self._cache[cache_key] = UserStreak.objects.filter(
                user_id=self.user_id, streak_type=streak_type
            ).first()
        return self._cache[cache_key]

    def _get_wallet(self):
        """Get user's wallet"""
        from db.task import Wallet

        if "wallet" not in self._cache:
            self._cache["wallet"] = Wallet.objects.filter(user_id=self.user_id).first()
        return self._cache["wallet"]

    def _get_total_task_count(self) -> int:
        """Get user's total approved task count"""
        from db.task import KarmaActivityLog

        if "total_tasks" not in self._cache:
            self._cache["total_tasks"] = KarmaActivityLog.objects.filter(
                user_id=self.user_id, appraiser_approved=True
            ).count()
        return self._cache["total_tasks"]
