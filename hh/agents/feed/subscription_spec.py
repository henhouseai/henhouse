from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Union
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)
@dataclass(frozen=True)
class SubscriptionSpec:
    key: str
    target_table: str
    target_id_field: str
    target_title_field: str
    subscription_table: str
    queue_table: str
    link_table: str
    link_id_field: str
    agent_validation: bool = True
    message_query_factory: Optional[Callable[[str], str]] = None
    message_filter_hook: Optional[Callable[[Dict[str, Union[str, int]]], bool]] = None
    
    def __post_init__(self):
        trace_in()
        required_fields = [
            'key', 'target_table', 'target_id_field', 'target_title_field',
            'subscription_table', 'queue_table', 'link_table', 'link_id_field'
        ]
        for field in required_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str) or not value.strip():
                warn(f"SubscriptionSpec.{field} cannot be empty or whitespace")
                trace_out()
                raise ValueError(f"SubscriptionSpec.{field} cannot be empty or whitespace")
        if not self.key.islower() or not self.key.replace('_', '').isalnum():
            warn(f"SubscriptionSpec.key must be lowercase alphanumeric with underscores only, got: '{self.key}'")
            trace_out()
            raise ValueError(f"SubscriptionSpec.key must be lowercase alphanumeric with underscores only, got: '{self.key}'")
        log(f"SubscriptionSpec validated: {self.key}")
        trace_out()

SUBSCRIPTION_SPECS: Dict[str, SubscriptionSpec] = {
    'step': SubscriptionSpec(
        key='step',
        target_table='steps',
        target_id_field='id',
        target_title_field='title',
        subscription_table='subscription_step',
        queue_table='watercooler_queue_step',
        link_table='wc_microlog_link_step',
        link_id_field='step_id'
    ),
    'task': SubscriptionSpec(
        key='task',
        target_table='tasks',
        target_id_field='id',
        target_title_field='title',
        subscription_table='subscription_task',
        queue_table='watercooler_queue_task',
        link_table='wc_microlog_link_task',
        link_id_field='task_id'
    ),
    'ask': SubscriptionSpec(
        key='ask',
        target_table='asks',
        target_id_field='id',
        target_title_field='title',
        subscription_table='subscription_ask',
        queue_table='watercooler_queue_ask',
        link_table='wc_microlog_link_ask',
        link_id_field='ask_id'
    ),
    'docket': SubscriptionSpec(
        key='docket',
        target_table='work_dockets',
        target_id_field='id',
        target_title_field='title',
        subscription_table='subscription_docket',
        queue_table='watercooler_queue_docket',
        link_table='wc_microlog_link_docket',
        link_id_field='docket_id'
    ),
    'sidecar': SubscriptionSpec(
        key='sidecar',
        target_table='sidecar_files',
        target_id_field='id',
        target_title_field='title',
        subscription_table='subscription_sidecar',
        queue_table='watercooler_queue_sidecar',
        link_table='wc_microlog_link_sidecar',
        link_id_field='sidecar_file_id'
    ),
    'keyword': SubscriptionSpec(
        key='keyword',
        target_table='keywords',
        target_id_field='id',
        target_title_field='keyword',
        subscription_table='subscription_keyword',
        queue_table='watercooler_queue_keyword',
        link_table='wc_microlog_link_keyword',
        link_id_field='keyword_id'
    ),
    'agent': SubscriptionSpec(
        key='agent',
        target_table='agents',
        target_id_field='id',
        target_title_field='agent_key',
        subscription_table='subscription_agent',
        queue_table='watercooler_queue_agent',
        link_table='wc_microlog_link_agent',
        link_id_field='target_agent_id'
    ),
    'operator': SubscriptionSpec(
        key='operator',
        target_table='agents',
        target_id_field='id',
        target_title_field='agent_key',
        subscription_table='subscription_operator',
        queue_table='watercooler_queue_operator',
        link_table='wc_microlog_link_operator',
        link_id_field='operator_id'
    )
}
