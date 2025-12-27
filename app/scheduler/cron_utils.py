"""
CRON Expression Parsing and Next Run Time Calculation
Supports CRON expressions with seconds: second minute hour day month weekday
"""
from datetime import datetime
from croniter import croniter
from typing import Optional

class CronUtils:
    """Utility class for CRON operations"""
    
    @staticmethod
    def validate_cron(expression: str) -> bool:
        """
        Validate a CRON expression with seconds support
        Format: second minute hour day month weekday
        Example: "0 */5 * * * *" (every 5 minutes)
        """
        try:
            # Check if expression has 6 parts (with seconds)
            parts = expression.strip().split()
            if len(parts) != 6:
                return False
            
            # Try to create croniter instance
            croniter(expression, datetime.now())
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_next_run_time(expression: str, base_time: Optional[datetime] = None) -> datetime:
        """
        Calculate the next run time for a CRON expression
        
        Args:
            expression: CRON expression with seconds (6 parts)
            base_time: Base time to calculate from (defaults to now)
        
        Returns:
            Next scheduled run time
        
        Raises:
            ValueError: If CRON expression is invalid
        """
        if not CronUtils.validate_cron(expression):
            raise ValueError(f"Invalid CRON expression: {expression}")
        
        if base_time is None:
            base_time = datetime.now()
        
        try:
            cron = croniter(expression, base_time)
            return cron.get_next(datetime)
        except Exception as e:
            raise ValueError(f"Error calculating next run time: {str(e)}")
    
    @staticmethod
    def get_previous_run_time(expression: str, base_time: Optional[datetime] = None) -> datetime:
        """Get the previous run time for a CRON expression"""
        if not CronUtils.validate_cron(expression):
            raise ValueError(f"Invalid CRON expression: {expression}")
        
        if base_time is None:
            base_time = datetime.now()
        
        try:
            cron = croniter(expression, base_time)
            return cron.get_prev(datetime)
        except Exception as e:
            raise ValueError(f"Error calculating previous run time: {str(e)}")
    
    @staticmethod
    def format_cron_description(expression: str) -> str:
        """
        Provide a human-readable description of the CRON expression
        """
        try:
            parts = expression.strip().split()
            if len(parts) != 6:
                return "Invalid CRON expression"
            
            second, minute, hour, day, month, weekday = parts
            
            # Simple descriptions for common patterns
            if expression == "0 * * * * *":
                return "Every minute"
            elif expression == "0 */5 * * * *":
                return "Every 5 minutes"
            elif expression == "0 0 * * * *":
                return "Every hour"
            elif expression == "0 0 0 * * *":
                return "Daily at midnight"
            else:
                return f"Custom: {expression}"
        except Exception:
            return "Invalid CRON expression"