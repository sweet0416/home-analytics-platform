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
    lottery_sync_source_unavailable = "LOTTERY_SYNC_SOURCE_UNAVAILABLE"
    lottery_sync_parse_failed = "LOTTERY_SYNC_PARSE_FAILED"
    lottery_sync_validation_failed = "LOTTERY_SYNC_VALIDATION_FAILED"
    lottery_sync_run_not_found = "LOTTERY_SYNC_RUN_NOT_FOUND"
    lottery_sync_already_running = "LOTTERY_SYNC_ALREADY_RUNNING"
