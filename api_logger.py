from datetime import datetime
import pytz
from typing import List, Dict
import json

class APILogger:
    def __init__(self):
        self.logs: List[Dict] = []
        self.max_logs = 1000  # Keep last 1000 logs
        
    def _get_ist_time(self) -> str:
        """Get current time in IST."""
        utc_now = datetime.now(pytz.UTC)
        ist = pytz.timezone('Asia/Kolkata')
        return utc_now.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S %Z')
        
    def log_request(self, endpoint: str, method: str, payload: Dict) -> None:
        """Log incoming API request."""
        log_entry = {
            "timestamp": self._get_ist_time(),
            "type": "request",
            "endpoint": endpoint,
            "method": method,
            "payload": payload
        }
        self.logs.append(log_entry)
        self._trim_logs()
        
    def log_response(self, endpoint: str, method: str, payload: Dict) -> None:
        """Log API response."""
        log_entry = {
            "timestamp": self._get_ist_time(),
            "type": "response",
            "endpoint": endpoint,
            "method": method,
            "payload": payload
        }
        self.logs.append(log_entry)
        self._trim_logs()
        
    def _trim_logs(self) -> None:
        """Keep only the most recent logs."""
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
            
    def get_logs(self) -> List[Dict]:
        """Get all logs."""
        return self.logs 