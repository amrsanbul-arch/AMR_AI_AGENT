export type AssistantIntent = "ideas" | "caption" | "reel" | "trends" | "analytics" | "profile" | "strategy" | "calendar";
export type ParsedCommand = { intent: AssistantIntent; topic: string | null } | null;
export function parseAssistantCommand(input: string): ParsedCommand;
