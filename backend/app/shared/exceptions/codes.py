from enum import StrEnum


class ErrorCode(StrEnum):
    validation_error = "VALIDATION_ERROR"
    not_found = "NOT_FOUND"
    internal_error = "INTERNAL_ERROR"
    plugin_not_found = "PLUGIN_NOT_FOUND"
    plugin_disabled = "PLUGIN_DISABLED"
    lottery_draw_not_found = "LOTTERY_DRAW_NOT_FOUND"
    lottery_rule_not_found = "LOTTERY_RULE_NOT_FOUND"
    lottery_invalid_numbers = "LOTTERY_INVALID_NUMBERS"

