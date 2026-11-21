// Query a local Ollama model that best fits the host hardware.
// Usage: npm run query -- --prompt "<text>" [--host <url>]
import os from "node:os";
import { execFile, spawn } from "node:child_process";
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

async function serverUp(ollama: Ollama): Promise<boolean> {
	try {
		await ollama.list();
		return true;
	} catch {
		return false;
	}
}

async function ensureServer(ollama: Ollama, host?: string): Promise<void> {
	if (await serverUp(ollama)) {
		return;
	}
	if (host) {
		throw new Error(`no Ollama server at ${host}`);
	}
	const serve = spawn("ollama", ["serve"], { stdio: "ignore" });
	const spawnError = new Promise<never>((_, reject) => {
		serve.on("error", () => {
			reject(new Error("ollama is not installed and no server is running"));
		});
	});
	const waitUp = (async () => {
		for (let attempt = 0; attempt < 40; attempt += 1) {
			if (await serverUp(ollama)) {
				return;
			}
			await new Promise((resolve) => setTimeout(resolve, 250));
		}
		serve.kill();
		throw new Error("started ollama serve but the server never came up");
	})();
	try {
		await Promise.race([waitUp, spawnError]);
	} catch (error) {
		serve.kill();
		throw error;
	}
}

async function main(): Promise<void> {
	const { values } = parseArgs({
		options: {
			prompt: { type: "string", required: true },
			host: { type: "string" },
		},
	});

	const ollama = new Ollama(values.host ? { host: values.host } : {});
	await ensureServer(ollama, values.host);

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
