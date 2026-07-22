import React, { useState, useEffect } from 'react';
import { Folder, File, RefreshCw, X, FolderOpen, Code } from 'lucide-react';

export default function WorkspaceViewer({ refreshTrigger, onOpenFile }) {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedDirs, setExpandedDirs] = useState({ '.': true });
  const [loadedData, setLoadedData] = useState({});

  const fetchDirectory = async (path = '.') => {
    try {
      const response = await fetch(`/api/workspace/files?path=${encodeURIComponent(path)}`);
      if (!response.ok) {
        throw new Error(`Failed to read directory '${path}'`);
      }
      const data = await response.json();
      return data.entries || [];
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  const loadWorkspaceRoot = async () => {
    setLoading(true);
    setError(null);
    try {
      const rootEntries = await fetchDirectory('.');
      setLoadedData({ '.': rootEntries });
      setTree(rootEntries);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Reload when triggered by agent changes
  useEffect(() => {
    loadWorkspaceRoot();
  }, [refreshTrigger]);

  const toggleDirectory = async (path) => {
    if (expandedDirs[path]) {
      // Collapse
      setExpandedDirs((prev) => ({ ...prev, [path]: false }));
    } else {
      // Load and expand
      const entries = await fetchDirectory(path);
      setLoadedData((prev) => ({ ...prev, [path]: entries }));
      setExpandedDirs((prev) => ({ ...prev, [path]: true }));
    }
  };

  const handleFileClick = async (path, name) => {
    try {
      const response = await fetch(`/api/workspace/file?path=${encodeURIComponent(path)}`);
      if (!response.ok) {
        throw new Error('Could not open file');
      }
      const data = await response.json();
      onOpenFile({
        name,
        path: data.path,
        content: data.content,
        size: data.size,
      });
    } catch (err) {
      alert(`Error reading file: ${err.message}`);
    }
  };

  // Helper to render tree nodes recursively
  const renderNodes = (entries, depth = 0, parentPath = '.') => {
    if (!entries || entries.length === 0) return null;

    return entries.map((entry) => {
      const isDir = entry.type === 'dir';
      const isExpanded = expandedDirs[entry.path];
      const children = loadedData[entry.path];

      return (
        <div key={entry.path} className="tree-node">
          <div
            className="tree-row"
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={() => {
              if (isDir) {
                toggleDirectory(entry.path);
              } else {
                handleFileClick(entry.path, entry.name);
              }
            }}
          >
            {isDir ? (
              isExpanded ? (
                <FolderOpen size={16} className="node-icon dir" />
              ) : (
                <Folder size={16} className="node-icon dir" />
              )
            ) : (
              <File size={16} className="node-icon" />
            )}
            <span className="node-name">{entry.name}</span>
            {!isDir && entry.size !== null && (
              <span className="node-size">{(entry.size / 1024).toFixed(1)} KB</span>
            )}
          </div>
          {isDir && isExpanded && children && renderNodes(children, depth + 1, entry.path)}
        </div>
      );
    });
  };

  return (
    <div className="app-workspace-panel">
      <div className="panel-header">
        <h3>
          <Code size={16} style={{ color: 'var(--color-primary-light)' }} />
          <span>WORKSPACE EXPLORER</span>
        </h3>
        <button className="refresh-btn" onClick={loadWorkspaceRoot} title="Refresh workspace">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="workspace-content">
        {loading && tree.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', marginTop: '2rem' }}>
            Loading files...
          </div>
        ) : error ? (
          <div style={{ color: 'var(--color-danger)', textAlign: 'center', marginTop: '2rem' }}>
            {error}
          </div>
        ) : tree.length === 0 ? (
          <div className="empty-workspace">
            <Folder size={32} opacity={0.4} />
            <div>Workspace is empty</div>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              Ask the agent to write files, and they will appear here.
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {renderNodes(tree)}
          </div>
        )}
      </div>
    </div>
  );
}
