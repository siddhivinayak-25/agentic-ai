import React, { useState, useEffect } from 'react';
import { Folder, File, RefreshCw, X, FolderOpen, Code, Database, Search } from 'lucide-react';

export default function WorkspaceViewer({ refreshTrigger, onOpenFile }) {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedDirs, setExpandedDirs] = useState({ '.': true });
  const [loadedData, setLoadedData] = useState({});
  
  // Search and indexing state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexingStatus, setIndexingStatus] = useState(null);

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
    if (searchQuery.trim()) {
      performSearch(searchQuery);
    }
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

  // Manual Workspace Indexing Trigger
  const handleIndexWorkspace = async () => {
    setIsIndexing(true);
    setIndexingStatus("Indexing workspace...");
    try {
      const response = await fetch('/api/workspace/index', { method: 'POST' });
      if (!response.ok) throw new Error("Indexing call failed");
      const data = await response.json();
      setIndexingStatus(`Indexed: ${data.files_indexed} changed, ${data.files_deleted_from_index} deleted.`);
      setTimeout(() => setIndexingStatus(null), 4000);
      loadWorkspaceRoot();
    } catch (err) {
      setIndexingStatus(`Error: ${err.message}`);
      setTimeout(() => setIndexingStatus(null), 4000);
    } finally {
      setIsIndexing(false);
    }
  };

  // Debounced search caller
  const performSearch = async (query) => {
    setIsSearching(true);
    try {
      const response = await fetch(`/api/workspace/search?query=${encodeURIComponent(query)}`);
      if (!response.ok) throw new Error("Search failed");
      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    if (!val.trim()) {
      setSearchResults([]);
      return;
    }
    performSearch(val);
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
      {/* Header */}
      <div className="panel-header">
        <h3>
          <Code size={16} style={{ color: 'var(--color-primary-light)' }} />
          <span>WORKSPACE EXPLORER</span>
        </h3>
        <button className="refresh-btn" onClick={loadWorkspaceRoot} title="Refresh workspace">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Code Search & Database Index Controls */}
      <div className="workspace-controls-section">
        <div className="search-bar-row">
          <div className="search-input-wrapper">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              className="workspace-search-input"
              placeholder="Search code..."
              value={searchQuery}
              onChange={handleSearchChange}
            />
            {searchQuery && (
              <button className="search-clear-btn" onClick={() => { setSearchQuery(''); setSearchResults([]); }}>
                <X size={12} />
              </button>
            )}
          </div>
          
          <button 
            className={`index-workspace-btn ${isIndexing ? 'indexing' : ''}`}
            onClick={handleIndexWorkspace}
            disabled={isIndexing}
            title="Index workspace files"
          >
            <Database size={14} className={isIndexing ? 'animate-spin' : ''} />
          </button>
        </div>
        {indexingStatus && (
          <div className="indexing-status-toast">
            {indexingStatus}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="workspace-content">
        {searchQuery.trim() ? (
          /* Search Results View */
          <div className="search-results-list">
            <div className="search-results-heading">Code Search Matches:</div>
            {isSearching && searchResults.length === 0 ? (
              <div className="search-feedback">Searching index...</div>
            ) : searchResults.length === 0 ? (
              <div className="search-feedback">No matching code found.</div>
            ) : (
              searchResults.map((res, index) => (
                <div 
                  key={index} 
                  className="search-result-item"
                  onClick={() => handleFileClick(res.file, res.file.split('/').pop())}
                >
                  <div className="search-result-meta">
                    <span className="file-link">{res.file}</span>
                    <span className="line-range">Lines {res.start_line}-{res.end_line}</span>
                  </div>
                  <pre className="search-result-snippet">{res.snippet}</pre>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Standard Folder Directory Tree View */
          loading && tree.length === 0 ? (
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
          )
        )}
      </div>
    </div>
  );
}
