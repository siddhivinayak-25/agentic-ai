import React, { useState, useRef, useEffect } from 'react';
import { Send, Terminal, Loader2, Sparkles, User, Shield } from 'lucide-react';
import StepView from './StepView';

export default function ChatInterface({ isRunning, setIsRunning, onWorkspaceChange }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [activeEvents, setActiveEvents] = useState([]);
  const messagesEndRef = useRef(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeEvents, isRunning]);

  const handleDemoPrompt = (promptText) => {
    if (isRunning) return;
    setInput(promptText);
    submitPrompt(promptText);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isRunning) return;
    submitPrompt(input);
  };

  const submitPrompt = async (promptText) => {
    const userPrompt = promptText.trim();
    setInput('');
    setIsRunning(true);
    setActiveEvents([]);

    // Add user message to history
    const newHistory = [...messages, { role: 'user', content: userPrompt }];
    setMessages(newHistory);

    try {
      // Build API request payload (format history for the backend)
      const chatHistory = [];
      newHistory.forEach((msg) => {
        // Only include final assistant text or user messages in history, simplified
        if (msg.role === 'user') {
          chatHistory.push({ role: 'user', content: msg.content });
        } else if (msg.role === 'assistant' && msg.content) {
          chatHistory.push({ role: 'assistant', content: msg.content });
        }
      });

      // Fetch the SSE response from backend
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userPrompt,
          history: chatHistory.slice(0, -1), // Exclude the last user prompt since it is sent in "message"
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Keep the last partial line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;

          try {
            const rawJson = trimmed.substring(6);
            const event = JSON.parse(rawJson);

            if (event.type === 'stream_end') {
              break;
            }

            // Append event to state
            setActiveEvents((prev) => [...prev, event]);
            
            // Check if this event created or changed files
            if (event.type === 'tool_result') {
              const name = event.data.name;
              if (name === 'write_file' || name === 'edit_file' || name === 'run_bash' || name === 'run_python_code' || name === 'run_python_file') {
                onWorkspaceChange?.();
              }
            }
          } catch (e) {
            console.error('Error parsing SSE line:', line, e);
          }
        }
      }
    } catch (err) {
      console.error('Stream failure:', err);
      setActiveEvents((prev) => [
        ...prev,
        {
          type: 'error',
          data: { message: `Failed to stream answer: ${err.message}` },
        },
      ]);
    } finally {
      setIsRunning(false);
      onWorkspaceChange?.(); // Trigger workspace tree refresh at the end
    }
  };

  // When stream ends, fold active events into a single assistant bubble
  useEffect(() => {
    if (!isRunning && activeEvents.length > 0) {
      let finalAnswer = '';
      const finalEvent = activeEvents.find((e) => e.type === 'final');
      if (finalEvent) {
        finalAnswer = finalEvent.data.text;
      } else {
        const lastThought = [...activeEvents].reverse().find((e) => e.type === 'thought');
        finalAnswer = lastThought ? lastThought.data.text : 'I have finished execution.';
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: finalAnswer,
          steps: activeEvents,
        },
      ]);
      setActiveEvents([]);
    }
  }, [isRunning, activeEvents]);

  const demoSuggestions = [
    {
      title: 'Generate a Fibonacci Script',
      prompt: 'Write a python file called fibonacci.py that prints the first 10 Fibonacci numbers, and then run it to verify.',
    },
    {
      title: 'Analyze text files',
      prompt: 'Create a log file logs.txt with 5 lines of sample log entries (some containing ERROR and INFO). Write a script to find and count lines with ERROR, execute it, and show the results.',
    },
    {
      title: 'Directory Operations',
      prompt: 'List the contents of the current directory, and read pyproject.toml line 1 to 10.',
    }
  ];

  return (
    <div className="app-chat-panel">
      <div className="chat-messages">
        {messages.length === 0 && activeEvents.length === 0 && (
          <div className="welcome-screen">
            <div className="welcome-icon">
              <Sparkles size={48} className="logo-icon" />
            </div>
            <h2 className="welcome-title">Antigravity Agent</h2>
            <p className="welcome-desc">
              A powerful agentic coding system. I can write files, search directories, and execute Python/bash commands inside a secure workspace jail.
            </p>
            <div className="demo-prompts">
              {demoSuggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  className="demo-prompt-btn"
                  onClick={() => handleDemoPrompt(suggestion.prompt)}
                  disabled={isRunning}
                >
                  <span>{suggestion.title}</span>
                  <Terminal size={14} />
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`message-bubble ${msg.role}`}>
            <div className="message-header">
              {msg.role === 'user' ? (
                <>
                  <User size={12} />
                  <span>You</span>
                </>
              ) : (
                <>
                  <Shield size={12} style={{ color: 'var(--color-primary-light)' }} />
                  <span>Agent</span>
                </>
              )}
            </div>
            <div className="message-content">
              {msg.content && <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>}
              {msg.steps && msg.steps.length > 0 && (
                <div className="agent-steps">
                  {msg.steps.map((step, sIdx) => (
                    <StepView key={sIdx} event={step} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live SSE Stream events */}
        {activeEvents.length > 0 && (
          <div className="message-bubble assistant">
            <div className="message-header">
              <Shield size={12} style={{ color: 'var(--color-primary-light)' }} />
              <span>Agent (Processing...)</span>
            </div>
            <div className="message-content">
              <div className="agent-steps">
                {activeEvents.map((step, sIdx) => (
                  <StepView key={sIdx} event={step} />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <input
            className="chat-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isRunning ? 'Agent is working...' : 'Ask the agent to code or run commands...'}
            disabled={isRunning}
          />
          <button
            type="submit"
            className="chat-submit-btn"
            disabled={!input.trim() || isRunning}
          >
            {isRunning ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Running</span>
              </>
            ) : (
              <>
                <Send size={16} />
                <span>Send</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
