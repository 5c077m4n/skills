// Runner: executes one pi task via the official SDK, non-interactively.
// Usage: npx tsx pi-run.ts "<task description>" (cwd = pi's work directory).
import { createAgentSession, DefaultResourceLoader, getAgentDir, SessionManager } from "@earendil-works/pi-coding-agent";

const task = process.argv[2];
if (!task) {
	console.error("usage: npx tsx pi-run.ts \"<task>\"");
	process.exit(2);
}

const resourceLoader = new DefaultResourceLoader({
	cwd: process.cwd(),
	agentDir: getAgentDir(),
});
await resourceLoader.reload();

const { session } = await createAgentSession({
	cwd: process.cwd(),
	resourceLoader,
	sessionManager: SessionManager.inMemory(),
});

try {
	session.subscribe((event) => {
		if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
			process.stdout.write(event.assistantMessageEvent.delta);
		}
	});
	await session.prompt(
		task +
			" Strict rule: do NOT run any git command. Work only inside this directory. " +
			"When finished, print ONLY the unified diff of every change you made — no prose, no summaries.",
	);
} finally {
	session.dispose();
}
