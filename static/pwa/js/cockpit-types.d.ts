/**
 * cockpit-types.d.ts — THE PANEL CONTRACT (TypeScript win #1: types first)
 *
 * The cockpit consumes shaped JSON from ~90 panel routes. This file pins the
 * shapes the cockpit actually reads, so field drift between Flask and the
 * PWA becomes visible in the editor instead of a silent UI break.
 *
 * Zero build step: plain JS files opt in with one line at the top —
 *     /// <reference path="./cockpit-types.d.ts" />
 * and hover/autocomplete type-checks immediately in VS Code. Flipping
 * `// @ts-check` on per-file turns checking strict, file by file.
 *
 * Sources of truth: cortex/brain_api.py, app.py routes, DOCUMENTATION.md §2.
 */

/** Standard panel envelope: {"success": true/false, ...} */
interface ApiResponse {
  success: boolean;
  /** present on 4xx: "objective requise", "message vide", ... */
  error?: string;
  /** human-readable result ("she heard you", "nothing to abort", ...) */
  message?: string;
}

/** One attached ADB device (adb devices -l row). */
interface DeviceEntry {
  serial: string;
  status: "device" | "offline" | "unauthorized" | "recovery";
  model?: string;
  [k: string]: unknown;
}

/** GET /api/devices */
interface DevicesResponse extends ApiResponse {
  devices: DeviceEntry[];
}

/** GET /api/device/status */
interface DeviceStatusResponse {
  connected: boolean;
  devices: DeviceEntry[];
  active_device: DeviceEntry | null;
}

/** GET /api/brain/status — the cockpit's main poll. */
interface BrainStatus {
  state: "idle" | "running";
  mode?: "task" | "chat";
  step: number;
  /** live narration lines (trimmed to last 60) */
  narration: string[];
  /** the final answer of the last mission (null while running) */
  final: string | null;
  /** honest fold reason: "provider refusal survived reframe + 2 wipes", ... */
  error: string | null;
  /** operator inbox not yet drained */
  inbox_pending?: number;
  chat_turns?: number;
  /** last thing she said in chat */
  chat_last?: string;
  persona?: string;
  model?: string;
  has_key?: boolean;
}

/** GET /api/brain/config */
interface BrainConfigResponse extends ApiResponse {
  provider: string;
  base_url: string;
  model: string;
  max_steps: number;
  max_chat_steps?: number;
  temperature?: number;
  persona_name: string;
  has_key: boolean;
  /** never the key itself — last 4 chars only */
  key_tail?: string;
}

/** POST /api/brain/task | /chat | /say | /stop | /chat/clear */
type BrainActionResponse = ApiResponse;

/** POST /api/brain/say body — the operator channel. "__ABORT__" folds. */
interface SayRequest {
  message: string;
}

/** POST /api/brain/task body */
interface TaskRequest {
  objective: string;
}

/** POST /api/brain/chat body */
interface ChatRequest {
  message: string;
}

/** Ghost hunter routes: /api/ghost/hunter/{arm,status,standdown} */
interface HunterResponse extends ApiResponse {
  armed?: boolean;
  targets?: Array<{ [k: string]: unknown }>;
  note?: string;
}

/** Cockpit global (app.js). */
interface Window {
  VesperCockpit: {
    pollStatus: () => void;
    [k: string]: unknown;
  };
}
