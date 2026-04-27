from . import (
    fayna_capi_event_log,
    fayna_capi_service,
    res_config_settings,
    sale_order,
)

# camp_support_request is only active when fayna_camp_sales is installed.
# Uncomment the import below and add 'fayna_camp_sales' to __manifest__.py
# depends when that module is available in the same environment.
# from . import camp_support_request
