import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { extname } from "node:path";

const blockedTrackedFiles = [
  /(^|\/)\.env(?:\.|$)/i,
  /(^|\/)\.envrc$/i,
  /(^|\/)\.npmrc$/i,
  /\.(?:pem|key|p12|pfx)$/i,
  /(^|\/)(?:credentials|service-account)(?:\.|\/)/i,
];

const textExtensions = new Set([
  "", ".cjs", ".css", ".csv", ".html", ".js", ".json", ".jsx", ".md",
  ".mjs", ".py", ".svg", ".ts", ".tsx", ".txt", ".xml", ".yaml", ".yml",
]);

const secretPatterns = [
  ["AWS access key", new RegExp("AK" + "IA[0-9A-Z]{16}", "g")],
  ["AWS temporary access key", new RegExp("AS" + "IA[0-9A-Z]{16}", "g")],
  ["GitHub token", new RegExp("gh" + "[pousr]_[A-Za-z0-9_]{30,}", "g")],
  ["GitHub fine-grained token", new RegExp("github" + "_pat_[A-Za-z0-9_]{30,}", "g")],
  ["OpenAI API key", new RegExp("sk" + "-(?:proj-)?[A-Za-z0-9_-]{30,}", "g")],
  ["Google API key", new RegExp("AI" + "za[0-9A-Za-z_-]{35}", "g")],
  ["Slack webhook", new RegExp("hooks\\.slack\\.com/services/[A-Za-z0-9/_-]{20,}", "g")],
  ["Slack token", new RegExp("xox" + "[baprs]-[A-Za-z0-9-]{10,}", "g")],
  ["Telegram bot token", new RegExp("[0-9]{8,10}:[A-Za-z0-9_-]{30,}", "g")],
  ["private key", new RegExp("BEGIN (?:RSA |EC |OPENSSH )?PRIVATE " + "KEY", "g")],
  ["hard-coded bearer token", new RegExp("Bearer\\s+[A-Za-z0-9._~-]{30,}", "g")],
  ["Korean resident registration number", new RegExp("(?:^|[^0-9])(?:[0-9]{6})-[1-8][0-9]{6}(?:[^0-9]|$)", "g")],
];

const files = execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" })
  .split("\0")
  .filter(Boolean);

const findings = [];
for (const file of files) {
  if (blockedTrackedFiles.some((pattern) => pattern.test(file))) {
    findings.push(`${file}: sensitive file type must not be tracked`);
    continue;
  }
  if (!textExtensions.has(extname(file).toLowerCase())) continue;

  let content;
  try {
    content = readFileSync(file, "utf8");
  } catch {
    continue;
  }
  if (content.includes("\0")) continue;

  for (const [label, pattern] of secretPatterns) {
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(content))) {
      const line = content.slice(0, match.index).split("\n").length;
      findings.push(`${file}:${line}: ${label}`);
      if (match.index === pattern.lastIndex) pattern.lastIndex += 1;
    }
  }
}

if (findings.length) {
  console.error("Public repository security check failed:");
  findings.forEach((finding) => console.error(`- ${finding}`));
  console.error("Remove the value from Git history and rotate the credential before merging.");
  process.exit(1);
}

console.log(`Public repository security check passed (${files.length} tracked files scanned).`);
