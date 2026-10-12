# Luna conversation checks

The aim is a responsive companion that uses the existing 40 faces appropriately and keeps a normal conversation. Tests use GPT-6 Luna with low reasoning. The native Codex voice service remains a separate speaking and listening layer; selecting Luna changes the tool and background models.

## Acceptance checks

- Every source face can be selected through a valid named preset and variant. Unavailable names and variants do not silently select a different face.
- Conversation retains corrections and preferences across turns. Replies fit the person's tone and requested length, avoid forced questions, and do not narrate internal tools or expression metadata.
- Sensor and motion claims match actual receipts. Preview commands never become claims of physical movement. Stale or absent readings remain unavailable.
- Tool calls serve the request. Ordinary chat does not require a sensor read, memory write, or background task. Expression changes stay bounded and old turns cannot restore an interrupted reaction.
- Stop and interruption take priority. A correction replaces the old answer. A request for quiet receives at most a brief acknowledgement.
- First text, first tool, first complete phrase, total response and cold connection timing are reported separately. Text or tool timing is not presented as audible voice latency.
- The same production prompts and schemas are exercised. Test-only tool receipts, input synthesis, shared account load and unavailable services are identified.

## Work

1. Freeze varied conversation arcs and face requests before running them. Preserve baseline transcripts and failures.
2. Run real Luna calls through the application adapter and the actual native delegation path. Use isolated preference files and no physical actuator transport.
3. Have an independent agent review replies and run adversarial integration checks. Mechanical checks alone cannot establish natural conversation.
4. Fix demonstrated prompt, schema or implementation defects. Rerun affected cases and a held-out conversation set.
5. Compare supported low-latency settings with matched requests. Keep a change only when the behavior or measurements justify it.
6. Restart the local service with the verified configuration and provide a readable report with example conversations, timings and remaining limitations.

## Provider availability

On 22 September, the configured MIST voice lookup succeeded but minimal ElevenLabs synthesis returned HTTP 401 payment_required. Subscription status was past_due. No payment settings were changed. Saved audio and deterministic playback tests remain usable. Fresh final-voice quality and physical phone audio delay cannot be certified while synthesis is blocked.
