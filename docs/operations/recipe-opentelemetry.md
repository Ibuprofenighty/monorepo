# Recipe: adding OpenTelemetry later

The template ships the instrumentation hooks, not the observability backend.
When you need distributed tracing / metrics collection, add OTel in an
afternoon — the hard parts are already done.

## What's already in the template (Batch C)

- **Trace propagation**: `TraceIdMiddleware` resolves the trace id per request
  (priority: W3C `traceparent` > `x-trace-id` > generated) and stores it in a
  `contextvar`. See `platform/observability/trace.py`.
- **Structured JSON logs**: every record carries `trace_id`, so logs join with
  traces. See `platform/observability/logging.py`.
- **Health probes**: `/api/v1/health` (liveness), `/api/v1/ready` (DB + Redis).

## Adding OTel (when you need it)

1. Add dependencies: `opentelemetry-api`, `opentelemetry-sdk`,
   `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`,
   `opentelemetry-instrumentation-sqlalchemy`.

2. In `bootstrap/app.py`, after `create_app` builds the app:
   ```python
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

   trace.set_tracer_provider(TracerProvider())
   trace.get_tracer_provider().add_span_processor(
       BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint))
   )
   ```

3. Bridge the template's trace id to OTel: in `TraceIdMiddleware`, after
   `set_trace_id(trace_id)`, set it as baggage or start the OTel span with
   the extracted `trace_id` as parent. The W3C `traceparent` parsing in
   `trace.py` gives you the exact 32-hex id to use.

4. Add Tempo/Prometheus/Grafana to `infra/compose/compose.yaml` (or use your
   cloud provider's managed backend — the template makes no choice here).

## What NOT to do

- Don't replace the template's `x-trace-id` propagation — OTel uses W3C
  `traceparent`, which the middleware already understands. They compose.
- Don't log inside hot paths just because you have tracing now. The JSON
  logger's `extra_fields` is for structured context, not debug spam.
