
import { Message, Role } from "../types";

// Orchestrator backend URL (Repo service on port 8001)
// Orchestrator backend URL (Repo service on port 8001)
const ORCHESTRATOR_URL = "http://localhost:8001";

export class OrchestratorService {
    /**
     * Send message to Orchestrator and stream the response.
     * Note: Current orchestrator implementation is blocking, so this simulated stream
     * yields the final message as a single chunk.
     */
    async *streamChat(history: Message[], userInput: string, sessionId: string) {
        try {
            console.log(`Sending to Orchestrator [${sessionId}]:`, userInput);

            const response = await fetch(`${ORCHESTRATOR_URL}/process/process`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    query: userInput,
                    session_id: sessionId,
                    // We could pass history here if the backend supported context
                    // context: { history } 
                }),
            });

            if (!response.ok) {
                // Handle HTTP errors
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.detail?.message || response.statusText;
                throw new Error(`Orchestrator error (${response.status}): ${errorMsg}`);
            }

            const data = await response.json();
            console.log("Orchestrator response:", data);

            // Extract the message to display to the user
            // Check multiple possible locations for the message
            // Extract the message to display to the user
            // Check multiple possible locations for the message
            let reply = "";

            // Check for AWAITING_USER_INPUT status (clarifications, confirmations, validation errors)
            if (data.status === "AWAITING_USER_INPUT") {
                // For validation errors and clarifications, the message is in routing_decision.response
                if (data.routing_decision?.response) {
                    reply = data.routing_decision.response;
                } else if (data.message) {
                    reply = data.message;
                } else {
                    reply = "Please provide more information.";
                }
            }
            // Check for success with execution results
            else if (data.status === "SUCCESS") {
                // Default natural success message if no specific message from backend
                let baseMessage = "I've successfully completed the task.";

                // If backend provided a specific descriptive message, use it (unless it's just "Success")
                if (data.message && data.message.length > 10 && data.message !== "Task completed successfully") {
                    baseMessage = data.message;
                }

                reply = baseMessage;

                // Check for file outputs in execution result
                let foundPath = "";

                if (data.execution_result) {
                    const execResult = data.execution_result;

                    // Look for explicit specific output fields commonly used
                    const outputFields = ['output_folder', 'output_file', 'output_path', 'file_path', 'report_path', 'excel_path'];

                    for (const field of outputFields) {
                        if (execResult[field] && typeof execResult[field] === 'string') {
                            foundPath = execResult[field];
                            break;
                        }
                    }

                    // If no direct field, check 'outputs' dictionary
                    if (!foundPath && execResult.outputs && typeof execResult.outputs === 'object') {
                        const outputs = execResult.outputs;
                        // Grab the first string value that looks like a path
                        for (const key in outputs) {
                            if (typeof outputs[key] === 'string' && (outputs[key].includes('/') || outputs[key].includes('\\'))) {
                                foundPath = outputs[key];
                                break;
                            }
                        }
                    }
                }

                // DATA.FILE_RESOLUTION IS INPUT FILES - DO NOT USE FOR OUTPUT PATH
                // Leaving this empty to prevent showing input template as output


                if (foundPath) {
                    // Determine if it's likely a file or folder based on extension
                    const hasExtension = foundPath.split('/').pop()?.includes('.') || foundPath.split('\\').pop()?.includes('.');
                    const label = hasExtension ? "Generated File" : "Output Folder";
                    const icon = hasExtension ? "📄" : "📂";

                    reply = `${baseMessage} ${icon}\n\n**${label}:**\n\`${foundPath}\``;
                } else {
                    // If no path, just ensure we have some message
                    if (!reply) reply = "Task completed successfully.";
                }

                // Add execution stats if available
                if (data.execution_result?.stats) {
                    const stats = data.execution_result.stats;
                    if (stats.total_records) {
                        reply += `\n\n**Statistics:**\nTotal Records: ${stats.total_records}`;
                    }
                }
            }
            // If not success (or no special handling needed), check standard message fields
            else if (data.message && typeof data.message === 'string') {
                reply = data.message;
            }
            // Check routing_decision.message
            else if (data.routing_decision?.message) {
                reply = data.routing_decision.message;
            }
            // Check for response field
            else if (data.response && typeof data.response === 'string') {
                reply = data.response;
            }
            // Check for reply field
            else if (data.reply && typeof data.reply === 'string') {
                reply = data.reply;
            }
            // Check for error details
            else if (data.detail?.message) {
                reply = `Error: ${data.detail.message}`;
            }
            // Fallback: stringify the full response for debugging
            else {
                console.warn("Unknown response format:", data);
                reply = data.message || data.response || data.reply ||
                    JSON.stringify(data, null, 2).slice(0, 500) ||
                    "Processed successfully (No display message returned).";
            }

            // Yield the message to the chat interface
            yield reply;

        } catch (error) {
            console.error("Orchestrator API Error:", error);
            yield `I encountered an error connecting to the system: ${error instanceof Error ? error.message : String(error)}`;
        }
    }
}

export const orchestrator = new OrchestratorService();
