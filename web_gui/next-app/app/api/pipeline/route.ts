import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import path from "path";
import fs from "fs";

const ROOT_DIR = path.resolve(process.cwd(), "..", "..");
const DEFAULT_DATASET = "real_time_scenarios_realistic";
const SCENARIOS_DIR = path.join(ROOT_DIR, DEFAULT_DATASET);
// Use runtime-only values so Turbopack doesn't try to resolve these as modules
function getPythonPath(): string {
  return process.env.PYTHON_PATH || "python";
}
function getRunnerPath(): string {
  return path.join(process.cwd(), "api_runner.py");
}

function runPython(args: string[]): Promise<NextResponse> {
  return new Promise<NextResponse>((resolve) => {
    execFile(
      getPythonPath(),
      [getRunnerPath(), ...args],
      { maxBuffer: 10 * 1024 * 1024, cwd: process.cwd() },
      (err, stdout, stderr) => {
        if (err && !stdout.includes("___JSON_START___")) {
          resolve(
            NextResponse.json(
              { error: stderr || err.message },
              { status: 500 }
            )
          );
          return;
        }
        const match = stdout.match(
          /___JSON_START___([\s\S]*?)___JSON_END___/
        );
        if (match && match[1]) {
          try {
            const parsed = JSON.parse(match[1].trim());
            if (parsed.error) {
              resolve(
                NextResponse.json(parsed, { status: 500 })
              );
            } else {
              resolve(NextResponse.json(parsed));
            }
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            resolve(
              NextResponse.json(
                { error: "Failed to parse Python output: " + msg, raw: stdout.slice(0, 500) },
                { status: 500 }
              )
            );
          }
        } else {
          resolve(
            NextResponse.json(
              { error: "No data from pipeline", stderr: stderr.slice(0, 1000), stdout: stdout.slice(0, 500) },
              { status: 500 }
            )
          );
        }
      }
    );
  });
}

export async function GET(req: NextRequest): Promise<NextResponse> {
  const { searchParams } = new URL(req.url);
  const action = searchParams.get("action");
  const folder = searchParams.get("folder") || DEFAULT_DATASET;

  if (action === "datasets") {
    const candidates = [
      { id: "real_time_scenarios_realistic", name: "Realistic (Enterprise R20-11)" },
      { id: "real_time_scenarios", name: "Original Benchmark" },
    ];
    return NextResponse.json(candidates);
  }

  if (action === "scenarios") {
    try {
      const targetDir = path.isAbsolute(folder)
        ? folder
        : path.join(ROOT_DIR, folder);

      const scenarios: { id: string; title: string; path: string }[] = [];
      if (fs.existsSync(targetDir)) {
        const dirs = fs.readdirSync(targetDir).sort();
        for (const d of dirs) {
          const fullPath = path.join(targetDir, d);
          if (
            fs.statSync(fullPath).isDirectory() &&
            fs.existsSync(path.join(fullPath, "before.arxml"))
          ) {
            let title = d;
            const notesFile = path.join(fullPath, "NOTES.md");
            if (fs.existsSync(notesFile)) {
              const lines = fs
                .readFileSync(notesFile, "utf-8")
                .split("\n");
              for (const line of lines) {
                if (line.trim().startsWith("#")) {
                  title = line.replace(/#/g, "").trim();
                  break;
                }
              }
            }
            scenarios.push({ id: d, title, path: fullPath });
          }
        }
      }
      return NextResponse.json(scenarios);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return NextResponse.json({ error: msg }, { status: 500 });
    }
  }

  const scenario = searchParams.get("scenario") || "01_jeep_uconnect";
  const runArgs = ["stages", scenario];
  if (folder) {
    runArgs.push(folder);
  }
  return runPython(runArgs);
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  try {
    const body = await req.json();
    const { before_content, after_content, roles_content } = body;

    const tmpDir = path.join(process.cwd(), "tmp_uploads");
    if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });

    const beforeFile = path.join(tmpDir, "upload_before.arxml");
    const afterFile = path.join(tmpDir, "upload_after.arxml");
    const rolesFile = path.join(tmpDir, "upload_roles.yaml");

    fs.writeFileSync(beforeFile, before_content, "utf-8");
    fs.writeFileSync(afterFile, after_content, "utf-8");

    const args = ["paths", beforeFile, afterFile];
    if (roles_content && roles_content.trim()) {
      fs.writeFileSync(rolesFile, roles_content, "utf-8");
      args.push(rolesFile);
    }

    return runPython(args);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
