import logging
import os
from typing import Tuple, Optional
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, send_from_directory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Constants for better maintainability and performance
RACE_DISTANCES = {
    'fivek': 5.0,
    'tenk': 10.0,
    'twentyk': 20.0,
    'half': 21.0975,
    'marathon': 42.195
}

class PaceConverter:
    """High-performance pace conversion utilities."""

    @staticmethod
    def minutes_per_km_to_km_per_hour(minutes: int, seconds: int) -> float:
        """Convert pace from min/km to km/h."""
        if minutes == 0 and seconds == 0:
            return 0.0
        total_minutes = minutes + seconds / 60.0
        return 60.0 / total_minutes

    @staticmethod
    def km_per_hour_to_minutes_per_km(pace: float) -> Tuple[int, int]:
        """Convert pace from km/h to min/km."""
        if pace <= 0:
            return 0, 0

        total_minutes = 60.0 / pace
        minutes = int(total_minutes)
        seconds = int((total_minutes - minutes) * 60)
        return minutes, seconds

    @staticmethod
    def calculate_race_times(minutes: int, seconds: int, custom_distance: float = 0) -> dict:
        """Calculate race times for various distances."""
        if minutes == 0 and seconds == 0:
            return {key: "0h0min0s" for key in RACE_DISTANCES.keys()}

        total_seconds_per_km = minutes * 60 + seconds

        def format_time(total_seconds: float) -> str:
            hours = int(total_seconds // 3600)
            remaining_seconds = total_seconds % 3600
            mins = int(remaining_seconds // 60)
            secs = int(remaining_seconds % 60)
            return f"{hours}h{mins}min{secs}s"

        results = {}
        for race_name, distance in RACE_DISTANCES.items():
            race_total_seconds = total_seconds_per_km * distance
            results[race_name] = format_time(race_total_seconds)

        if custom_distance > 0:
            custom_total_seconds = total_seconds_per_km * custom_distance
            results['custom'] = format_time(custom_total_seconds)
        else:
            results['custom'] = "0h0min0s"

        return results

    @staticmethod
    def race_time_to_pace(race_distance: str, hours: int, minutes: int, seconds: int) -> Tuple[int, int]:
        """Convert race time to pace per km."""
        if race_distance not in RACE_DISTANCES:
            return 0, 0

        distance_km = RACE_DISTANCES[race_distance]
        total_race_seconds = hours * 3600 + minutes * 60 + seconds

        if total_race_seconds <= 0 or distance_km <= 0:
            return 0, 0

        seconds_per_km = total_race_seconds / distance_km
        pace_minutes = int(seconds_per_km // 60)
        pace_seconds = int(seconds_per_km % 60)

        return pace_minutes, pace_seconds

class InputValidator:
    """Input validation utilities."""

    @staticmethod
    def validate_pace_input(minutes_str: str, seconds_str: str) -> Tuple[bool, Optional[Tuple[int, int]], str]:
        """Validate and convert pace input."""
        try:
            minutes = int(minutes_str)
            seconds = int(seconds_str)

            if minutes < 0 or seconds < 0:
                return False, None, "Minutes and seconds must be non-negative"
            if seconds >= 60:
                return False, None, "Seconds must be less than 60"
            if minutes > 120:
                return False, None, "Minutes seems unreasonably high (>120)"

            return True, (minutes, seconds), ""

        except (ValueError, TypeError):
            return False, None, "Invalid input: please enter valid numbers"

    @staticmethod
    def validate_speed_input(speed_str: str) -> Tuple[bool, Optional[float], str]:
        """Validate and convert speed input."""
        try:
            speed = float(speed_str)

            if speed <= 0:
                return False, None, "Speed must be positive"
            if speed > 50:
                return False, None, "Speed seems unreasonably high (>50 km/h)"

            return True, speed, ""

        except (ValueError, TypeError, InvalidOperation):
            return False, None, "Invalid input: please enter a valid number"

    @staticmethod
    def validate_race_time_input(hours_str: str, minutes_str: str, seconds_str: str) -> Tuple[bool, Optional[Tuple[int, int, int]], str]:
        """Validate and convert race time input."""
        try:
            hours = int(hours_str or "0")
            minutes = int(minutes_str or "0")
            seconds = int(seconds_str or "0")

            if hours < 0 or minutes < 0 or seconds < 0:
                return False, None, "Time values must be non-negative"
            if minutes >= 60 or seconds >= 60:
                return False, None, "Minutes and seconds must be less than 60"
            if hours > 12:
                return False, None, "Race time seems unreasonably long (>12 hours)"
            if hours == 0 and minutes == 0 and seconds == 0:
                return False, None, "Please enter a valid race time"

            return True, (hours, minutes, seconds), ""

        except (ValueError, TypeError):
            return False, None, "Invalid input: please enter valid numbers"

@app.route("/", methods=['GET', 'POST'])
def index():
    """Main route handling pace conversions."""

    if request.method == 'GET':
        logger.info("GET request to index page")
        return render_template('mainpage.html',
                             minutes=0, seconds=0, pace=0,
                             fivek=0, tenk=0, twentyk=0,
                             half=0, marathon=0, o=0,
                             race_distance='', race_hours=0,
                             race_minutes=0, race_seconds=0)

    # POST request handling
    logger.info(f"POST request with form data: {dict(request.form)}")

    try:
        if 'converttokmperh' in request.form:
            return _handle_pace_to_speed_conversion()
        elif 'converttominperkm' in request.form:
            return _handle_speed_to_pace_conversion()
        elif 'convertfromracetime' in request.form:
            return _handle_race_time_conversion()
        else:
            logger.warning("Unknown form action in POST request")
            return render_template('mainpage.html',
                                 minutes=0, seconds=0, pace=0,
                                 fivek=0, tenk=0, twentyk=0,
                                 half=0, marathon=0, o=0)

    except Exception as e:
        logger.error(f"Unexpected error in index route: {e}")
        return render_template('mainpage.html',
                             minutes=0, seconds=0, pace=0,
                             fivek=0, tenk=0, twentyk=0,
                             half=0, marathon=0, o=0,
                             error="An unexpected error occurred")

def _handle_pace_to_speed_conversion():
    """Handle conversion from pace (min/km) to speed (km/h)."""
    minutes_str = request.form.get('minutes', '0')
    seconds_str = request.form.get('seconds', '0')

    is_valid, pace_data, error_msg = InputValidator.validate_pace_input(minutes_str, seconds_str)

    if not is_valid:
        logger.warning(f"Invalid pace input: {error_msg}")
        return render_template('mainpage.html',
                             minutes=0, seconds=0, pace=0,
                             fivek=0, tenk=0, twentyk=0,
                             half=0, marathon=0, o=0,
                             error=error_msg)

    minutes, seconds = pace_data
    speed = PaceConverter.minutes_per_km_to_km_per_hour(minutes, seconds)
    race_times = PaceConverter.calculate_race_times(minutes, seconds)

    logger.info(f"Converted pace {minutes}:{seconds:02d} to speed {speed:.2f} km/h")

    return render_template('mainpage.html',
                         minutes=minutes, seconds=seconds, pace=f"{speed:.2f}",
                         fivek=race_times['fivek'], tenk=race_times['tenk'],
                         twentyk=race_times['twentyk'], half=race_times['half'],
                         marathon=race_times['marathon'], o=race_times['custom'],
                         race_distance='', race_hours=0,
                         race_minutes=0, race_seconds=0)

def _handle_speed_to_pace_conversion():
    """Handle conversion from speed (km/h) to pace (min/km)."""
    speed_str = request.form.get('kmperhour', '0')

    is_valid, speed, error_msg = InputValidator.validate_speed_input(speed_str)

    if not is_valid:
        logger.warning(f"Invalid speed input: {error_msg}")
        return render_template('mainpage.html',
                             minutes=0, seconds=0, pace=0,
                             fivek=0, tenk=0, twentyk=0,
                             half=0, marathon=0, o=0,
                             error=error_msg)

    minutes, seconds = PaceConverter.km_per_hour_to_minutes_per_km(speed)
    race_times = PaceConverter.calculate_race_times(minutes, seconds)

    logger.info(f"Converted speed {speed} km/h to pace {minutes}:{seconds:02d}")

    return render_template('mainpage.html',
                         minutes=minutes, seconds=seconds, pace=speed_str,
                         fivek=race_times['fivek'], tenk=race_times['tenk'],
                         twentyk=race_times['twentyk'], half=race_times['half'],
                         marathon=race_times['marathon'], o=race_times['custom'],
                         race_distance='', race_hours=0,
                         race_minutes=0, race_seconds=0)

def _handle_race_time_conversion():
    """Handle conversion from race time to pace and other race times."""
    race_distance = request.form.get('race_distance', '')
    hours_str = request.form.get('race_hours', '0')
    minutes_str = request.form.get('race_minutes', '0')
    seconds_str = request.form.get('race_seconds', '0')

    if race_distance not in RACE_DISTANCES:
        logger.warning(f"Invalid race distance: {race_distance}")
        return render_template('mainpage.html',
                             minutes=0, seconds=0, pace=0,
                             fivek=0, tenk=0, twentyk=0,
                             half=0, marathon=0, o=0,
                             error="Please select a valid race distance")

    is_valid, time_data, error_msg = InputValidator.validate_race_time_input(hours_str, minutes_str, seconds_str)

    if not is_valid:
        logger.warning(f"Invalid race time input: {error_msg}")
        return render_template('mainpage.html',
                             minutes=0, seconds=0, pace=0,
                             fivek=0, tenk=0, twentyk=0,
                             half=0, marathon=0, o=0,
                             error=error_msg)

    hours, minutes_race, seconds_race = time_data
    pace_minutes, pace_seconds = PaceConverter.race_time_to_pace(race_distance, hours, minutes_race, seconds_race)
    speed = PaceConverter.minutes_per_km_to_km_per_hour(pace_minutes, pace_seconds)
    race_times = PaceConverter.calculate_race_times(pace_minutes, pace_seconds)

    logger.info(f"Converted {race_distance} time {hours}:{minutes_race:02d}:{seconds_race:02d} to pace {pace_minutes}:{pace_seconds:02d}")

    return render_template('mainpage.html',
                         minutes=pace_minutes, seconds=pace_seconds, pace=f"{speed:.2f}",
                         fivek=race_times['fivek'], tenk=race_times['tenk'],
                         twentyk=race_times['twentyk'], half=race_times['half'],
                         marathon=race_times['marathon'], o=race_times['custom'],
                         race_distance=race_distance, race_hours=hours,
                         race_minutes=minutes_race, race_seconds=seconds_race)

@app.route('/js/<path:path>')
def send_js(path):
    """Serve JavaScript files."""
    logger.debug(f"Serving JS file: {path}")
    return send_from_directory('js', path)

@app.route('/css/<path:path>')
def send_css(path):
    """Serve CSS files."""
    logger.debug(f"Serving CSS file: {path}")
    return send_from_directory('css', path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"

    logger.info(f"Starting Flask app on port {port}, debug={debug_mode}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)