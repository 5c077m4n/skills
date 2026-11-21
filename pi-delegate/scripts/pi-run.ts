// Runner: executes one pi task via the official SDK, non-interactively.
// Usage: npx tsx pi-run.ts --task "<task description>" [--cwd <dir>].
import { parseArgs } from "node:util";
import { createAgentSession, DefaultResourceLoader, getAgentDir, SessionManager } from "@earendil-works/pi-coding-agent";

const { values } = parseArgs({
	options: {
		cwd: { type: "string" },
		task: { type: "string", required: true },
	},
});
if (!values.task) {
	console.error("usage: npx tsx pi-run.ts --task \"<task>\" [--cwd <dir>]");
	process.exit(2);
}
const cwd = values.cwd ?? process.cwd();

const resourceLoader = new DefaultResourceLoader({
	cwd,
	agentDir: getAgentDir(),
	systemPromptOverride: (base) => `${base}\n\nStrict rules:\n- Do NOT run any git command.\n- Work only inside this directory.\n- When finished, print ONLY the unified diff of every change you made — no prose, no summaries.`,
});
await resourceLoader.reload();

const { session } = await createAgentSession({
	cwd,
	resourceLoader,
	sessionManager: SessionManager.create(cwd),
});

try {
	session.subscribe((event) => {
		if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
			process.stdout.write(event.assistantMessageEvent.delta);
		}
	});
	await session.prompt(values.task);
} catch (error) {
	console.error("pi-run failed:", error);
	process.exit(1);
} finally {
	session.dispose();
}
