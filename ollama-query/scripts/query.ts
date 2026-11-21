// Query a local Ollama model that best fits the host hardware.
// Usage: npm run query -- --prompt "<text>" [--host <url>]
import os from "node:os";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { parseArgs } from "node:util";
import { Ollama } from "ollama";

const execFileAsync = promisify(execFile);

const MEMORY_FRACTION = 0.7;

async function vramBytes(): Promise<number> {
	try {
		const { stdout } = await execFileAsync("nvidia-smi", [
			"--query-gpu=memory.total",
			"--format=csv,noheader,nounits",
		]);
		return stdout
			.trim()
			.split("\n")
			.map(Number)
			.reduce((total, mib) => total + mib * 1024 * 1024, 0);
	} catch {
		return 0;
	}
}

async function budgetBytes(): Promise<number> {
	const vram = await vramBytes();
	return vram > 0 ? vram * MEMORY_FRACTION : os.totalmem() * MEMORY_FRACTION;
}

async function bestModel(ollama: Ollama): Promise<string> {
	const { models } = await ollama.list();
	const budget = await budgetBytes();
	const fits = models.filter((model) => model.size <= budget);
	if (fits.length === 0) {
		throw new Error(
			`no local model fits ${(budget / 1e9).toFixed(1)} GB of usable memory; pull a smaller model with "ollama pull"`,
		);
	}
	fits.sort((a, b) => b.size - a.size);
	return fits[0].model;
}

async function main(): Promise<void> {
	const { values } = parseArgs({
		options: {
			prompt: { type: "string", required: true },
			host: { type: "string" },
		},
	});

	const ollama = new Ollama(values.host ? { host: values.host } : {});

	const model = await bestModel(ollama);
	console.error(`using ${model}`);

	const stream = await ollama.chat({
		model,
		messages: [{ role: "user", content: values.prompt }],
		stream: true,
	});
	for await (const part of stream) {
		process.stdout.write(part.message.content);
	}
	process.stdout.write("\n");
}

try {
	await main();
} catch (error) {
	console.error("ollama-query failed:", error);
	process.exit(1);
}
