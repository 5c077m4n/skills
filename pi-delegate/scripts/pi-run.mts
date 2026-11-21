// Runner: executes one pi task via the official SDK, non-interactively.
// Usage: npx tsx pi-run.mts "<task description>" (cwd = pi's work directory).
import { createAgentSession, ModelRuntime, SessionManager } from "@earendil-works/pi-coding-agent";

const task = process.argv[2];
if (!task) {
	console.error("usage: npx tsx pi-run.mts \"<task>\"");
	process.exit(2);
}

const modelRuntime = await ModelRuntime.create();

const { session } = await createAgentSession({
	cwd: process.cwd(),
	modelRuntime,
	sessionManager: SessionManager.inMemory(),
});

try {
	session.subscribe((event) => {
		if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
			process.stdout.write(event.assistantMessageEvent.delta);
		}
	});
	await session.prompt(task + " Strict rule: do NOT run any git command. Work only inside this directory.");
} finally {
	session.dispose();
}
