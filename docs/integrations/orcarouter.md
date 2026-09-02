# OrcaRouter integration

Antarctic Atlas can use OrcaRouter as an optional OpenAI-compatible provider
for the Research Universe classifier and paper-grounded answer flow.

## Configure the desktop app

The provider is disabled until a key is supplied. Before launching the current
Qt desktop source, set the key in the environment:

```zsh
export ORCAROUTER_API_KEY="sk-orca-your-key"
.venv/bin/python desktop_qt_app.py
```

You can also choose **OrcaRouter** in the Research Universe provider menu and
enter a key for the current session. The app never writes that session key to
the repository or application settings.

The default endpoint is `https://api.orcarouter.ai/v1` and the default model is
`gpt-4o`. The client calls the OpenAI-compatible
`/chat/completions` route and supports both complete and streamed responses.

## Verify the endpoint directly

Use a placeholder only in documentation. Replace it locally with your own key
and do not commit the command containing the real value:

```zsh
curl https://api.orcarouter.ai/v1/chat/completions \
  -H "Authorization: Bearer sk-orca-your-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Reply with exactly: connection-ok"}]}'
```

The in-app **Use & Test OrcaRouter** action performs the same kind of
connectivity check and reports a readable model response.

## Privacy boundary

Evidence-only mode never calls OrcaRouter. When OrcaRouter is selected, the
current question and the locally retrieved paper passages for that request are
sent to the provider. Antarctic Atlas does not send the complete PDF or
telemetry. OrcaRouter's own terms and privacy policy apply to requests sent to
its service.

For keys and account setup, use the project's
[OrcaRouter referral link](https://www.orcarouter.ai/ref/ref_1805b7cd8efbec534770).
