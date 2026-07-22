import React, { useState } from 'react';
import { Sparkles, X, Terminal, FileCode } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import WorkspaceViewer from './components/WorkspaceViewer';

export default function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [workspaceRefreshKey, setWorkspaceRefreshKey] = useState(0);
  const [openedFile, setOpenedFile] = useState(null);

  const triggerWorkspaceRefresh = () => {
    setWorkspaceRefreshKey((prev) => prev + 1);
  };

  const handleOpenFile = (fileDetails) => {
    setOpenedFile(fileDetails);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-section">
          <Sparkles size={22} className="logo-icon" />
          <h1 className="app-title">Antigravity Code</h1>
        </div>
        <div className="status-indicator">
          <div className={`status-dot ${isRunning ? 'running' : 'active'}`} />
          <span>{isRunning ? 'AGENT ACTIVE' : 'AGENT IDLE'}</span>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="app-main">
        <ChatInterface
          isRunning={isRunning}
          setIsRunning={setIsRunning}
          onWorkspaceChange={triggerWorkspaceRefresh}
        />
        <WorkspaceViewer
          refreshTrigger={workspaceRefreshKey}
          onOpenFile={handleOpenFile}
        />
      </main>

      {/* File Drawer Slideout Code Viewer */}
      <div className={`file-drawer ${openedFile ? 'open' : ''}`}>
        <div className="drawer-header">
          <div className="drawer-title-wrapper">
            <FileCode size={18} style={{ color: 'var(--color-primary-light)' }} />
            <div>
              <div className="drawer-title">{openedFile?.name}</div>
              <div className="drawer-subtitle">{openedFile?.path}</div>
            </div>
          </div>
          <button className="close-btn" onClick={() => setOpenedFile(null)}>
            <X size={16} />
          </button>
        </div>
        <div className="drawer-content">
          <pre className="drawer-code-pre">
            <code>{openedFile?.content}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
