from .help_cmd import register as register_help
from .morning_cmd import register as register_morning
from .setcalendar_cmd import register as register_setcalendar
from .setlocation_cmd import register as register_setlocation
from .status_cmd import register as register_status
from .today_cmd import register as register_today


def register_all_commands(bot) -> None:
    register_help(bot)
    register_setcalendar(bot)
    register_setlocation(bot)
    register_today(bot)
    register_morning(bot)
    register_status(bot)
