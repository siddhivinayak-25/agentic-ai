import React, { useState } from 'react';
import { Brain, Wrench, CheckCircle2, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';

export default function StepView({ event }) {
  const [isOpen, setIsOpen] = useState(true);
  const { type, data } = event;

  const toggleOpen = () => setIsOpen(!isOpen);

  // Determine icon and colors based on event type
  let title = '';
  let Icon = Brain;
  let headerClass = '';

  if (type === 'thought') {
    title = `Thought (Step ${data.step !== undefined ? data.step + 1 : ''})`;
    Icon = Brain;
    headerClass = 'step-type-thought';
  } else if (type === 'tool_call') {
    title = `Tool Call: ${data.name}`;
    Icon = Wrench;
    headerClass = 'step-type-tool_call';
  } else if (type === 'tool_result') {
    const isError = data.result && data.result.error;
    title = `Tool Result: ${data.name} ${isError ? '(Failed)' : '(Success)'}`;
    Icon = isError ? AlertTriangle : CheckCircle2;
    headerClass = isError ? 'text-rose-400' : 'step-type-tool_result';
  }

  // Format arguments or results into clean strings
  let bodyContent = null;
  if (type === 'thought') {
    bodyContent = <div className="thought-text">{data.text}</div>;
  } else if (type === 'tool_call') {
    let parsedArgs = data.arguments;
    if (typeof parsedArgs === 'string') {
      try {
        parsedArgs = JSON.parse(parsedArgs);
      } catch (e) {
        // Fallback if not valid JSON
      }
    }
    bodyContent = (
      <div>
        <div style={{ color: 'var(--color-text-muted)', marginBottom: '0.2rem' }}>Arguments:</div>
        <pre className="code-block">
          {typeof parsedArgs === 'object' 
            ? JSON.stringify(parsedArgs, null, 2) 
            : data.arguments}
        </pre>
      </div>
    );
  } else if (type === 'tool_result') {
    const res = data.result;
    const isError = res && res.error;
    
    bodyContent = (
      <div>
        <div style={{ color: 'var(--color-text-muted)', marginBottom: '0.2rem' }}>Returned:</div>
        <pre className={`code-block ${isError ? 'error' : 'result'}`}>
          {typeof res === 'object' ? JSON.stringify(res, null, 2) : String(res)}
        </pre>
      </div>
    );
  }

  return (
    <div className="step-card">
      <div className={`step-header ${headerClass}`} onClick={toggleOpen}>
        <div className="step-header-left">
          <Icon size={16} />
          <span>{title}</span>
        </div>
        <div>
          {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </div>
      {isOpen && (
        <div className="step-content">
          {bodyContent}
        </div>
      )}
    </div>
  );
}
