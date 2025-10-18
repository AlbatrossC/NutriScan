import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import pytz

class DatabaseLogger:
    def __init__(self):
        self.db_url = os.environ.get("DATABASE_LOGS_URL")
        self.enabled = self.db_url is not None
        
        if self.enabled:
            self._init_table()
    
    def _get_connection(self):
        """Create a database connection"""
        if not self.enabled:
            return None
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def _init_table(self):
        """Initialize the nutriscan_logs table if it doesn't exist"""
        try:
            conn = self._get_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nutriscan_logs (
                    serial_no SERIAL PRIMARY KEY,
                    date VARCHAR(10) NOT NULL,
                    time VARCHAR(20) NOT NULL,
                    input_text TEXT NOT NULL,
                    output_text TEXT,
                    error_type VARCHAR(255)
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error initializing table: {e}")
    
    def log_analysis(self, input_text, output_text=None, error_type=None):
        """
        Log analysis to database
        
        Args:
            input_text: The input text that was analyzed
            output_text: The output from Gemini (JSON string or dict)
            error_type: Error type if any error occurred
        """
        if not self.enabled:
            return
        
        try:
            # Get IST time
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            date_str = now.strftime('%d/%m/%Y')
            time_str = now.strftime('%I:%M:%S %p')
            
            # Convert output_text to string if it's a dict
            if isinstance(output_text, dict):
                import json
                output_text = json.dumps(output_text)
            
            conn = self._get_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO nutriscan_logs (date, time, input_text, output_text, error_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (date_str, time_str, input_text, output_text, error_type))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Error logging to database: {e}")

# Create a singleton instance
db_logger = DatabaseLogger()