import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Folder,
  FolderOpen,
  File,
  FileCode,
  FileText,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Search,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  ShieldCheck,
  Code2,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

/**
 * Format raw byte size into human-readable string.
 */
function formatBytes(bytes) {
  if (bytes === undefined || bytes === null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Deterministically pick an icon based on file extension.
 */
function getFileIcon(filename) {
  const ext = filename.split(".").pop().toLowerCase();
  switch (ext) {
    case "js":
    case "jsx":
    case "ts":
    case "tsx":
    case "py":
    case "java":
    case "cpp":
    case "c":
    case "cs":
    case "go":
    case "rs":
    case "php":
    case "rb":
    case "html":
    case "css":
    case "scss":
    case "sql":
      return <FileCode size={15} className="wfe-file-icon code" />;
    case "json":
    case "yaml":
    case "yml":
    case "toml":
    case "xml":
      return <FileText size={15} className="wfe-file-icon config" />;
    case "md":
    case "txt":
      return <FileText size={15} className="wfe-file-icon text" />;
    default:
      return <File size={15} className="wfe-file-icon" />;
  }
}

/**
 * Build a hierarchical folder tree from flat list of files and directories.
 */
function buildTree(directories, files) {
  const root = { dirs: {}, files: [] };

  function getDirNode(dirPath) {
    const parts = dirPath.split("/").filter(Boolean);
    let curr = root;
    let pathAcc = "";
    for (const part of parts) {
      pathAcc = pathAcc ? `${pathAcc}/${part}` : part;
      if (!curr.dirs[part]) {
        curr.dirs[part] = { name: part, path: pathAcc, dirs: {}, files: [] };
      }
      curr = curr.dirs[part];
    }
    return curr;
  }

  for (const dir of directories) {
    getDirNode(dir.path);
  }

  for (const file of files) {
    const slashIdx = file.path.lastIndexOf("/");
    if (slashIdx === -1) {
      root.files.push(file);
    } else {
      const parentDirPath = file.path.substring(0, slashIdx);
      const parentNode = getDirNode(parentDirPath);
      parentNode.files.push(file);
    }
  }

  return root;
}

export default function WorkspaceFileExplorer({ workspace, authFetch }) {
  const [files, setFiles] = useState([]);
  const [directories, setDirectories] = useState([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [filesError, setFilesError] = useState(null);

  const [selectedFilePath, setSelectedFilePath] = useState(null);
  const [selectedFileContent, setSelectedFileContent] = useState(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [contentError, setContentError] = useState(null);

  const [filterQuery, setFilterQuery] = useState("");
  const [expandedDirs, setExpandedDirs] = useState(new Set());
  const [copied, setCopied] = useState(false);

  // Fetch workspace file list
  const fetchFiles = useCallback(async () => {
    if (!workspace?.id) return;
    setIsLoadingFiles(true);
    setFilesError(null);
    try {
      const res = await authFetch(`/api/workspaces/${workspace.id}/files?recursive=true`);
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to load files (${res.status})`);
      }
      const data = await res.json();
      const filesList = data.files || [];
      const dirsList = data.directories || [];
      setFiles(filesList);
      setDirectories(dirsList);

      // Auto-expand all top-level directories
      const dirPaths = new Set(dirsList.map((d) => d.path));
      setExpandedDirs(dirPaths);
    } catch (err) {
      setFilesError(err.message || "Failed to load files.");
    } finally {
      setIsLoadingFiles(false);
    }
  }, [workspace?.id, authFetch]);

  // Load files whenever workspace changes
  useEffect(() => {
    setSelectedFilePath(null);
    setSelectedFileContent(null);
    setContentError(null);
    fetchFiles();
  }, [fetchFiles]);

  // Read file content safely
  const handleSelectFile = useCallback(
    async (filePath) => {
      if (!workspace?.id || !filePath) return;
      setSelectedFilePath(filePath);
      setIsLoadingContent(true);
      setContentError(null);
      setSelectedFileContent(null);
      try {
        const res = await authFetch(
          `/api/workspaces/${workspace.id}/files/content?path=${encodeURIComponent(filePath)}`
        );
        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(errData?.detail || `Failed to read file (${res.status})`);
        }
        const data = await res.json();
        setSelectedFileContent(data);
      } catch (err) {
        setContentError(err.message || "Failed to read file.");
      } finally {
        setIsLoadingContent(false);
      }
    },
    [workspace?.id, authFetch]
  );

  // Toggle directory expand/collapse
  const toggleDir = useCallback((dirPath) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(dirPath)) {
        next.delete(dirPath);
      } else {
        next.add(dirPath);
      }
      return next;
    });
  }, []);

  // Copy code to clipboard
  const handleCopy = () => {
    if (!selectedFileContent?.content) return;
    navigator.clipboard.writeText(selectedFileContent.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Filtered files when user types in search box
  const filteredFiles = useMemo(() => {
    if (!filterQuery.trim()) return null;
    const q = filterQuery.toLowerCase();
    return files.filter((f) => f.path.toLowerCase().includes(q));
  }, [files, filterQuery]);

  // Build tree structure
  const tree = useMemo(() => buildTree(directories, files), [directories, files]);

  // Recursive renderer for directory node
  const renderDirNode = (node, depth = 0) => {
    const isExpanded = expandedDirs.has(node.path);
    const dirNames = Object.keys(node.dirs).sort((a, b) => a.localeCompare(b));
    const sortedFiles = [...node.files].sort((a, b) => a.name.localeCompare(b.name));

    return (
      <div key={node.path} className="wfe-dir-wrapper">
        <button
          className="wfe-tree-row wfe-dir-row"
          style={{ paddingLeft: `${depth * 14 + 10}px` }}
          onClick={() => toggleDir(node.path)}
          title={node.path}
        >
          <span className="wfe-chevron">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
          <span className="wfe-folder-icon">
            {isExpanded ? <FolderOpen size={15} /> : <Folder size={15} />}
          </span>
          <span className="wfe-node-name">{node.name}</span>
        </button>

        {isExpanded && (
          <div className="wfe-dir-children">
            {dirNames.map((childDirName) =>
              renderDirNode(node.dirs[childDirName], depth + 1)
            )}
            {sortedFiles.map((f) => renderFileRow(f, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  // Renderer for a file row
  const renderFileRow = (file, depth = 0) => {
    const isSelected = selectedFilePath === file.path;
    return (
      <button
        key={file.path}
        className={`wfe-tree-row wfe-file-row ${isSelected ? "active" : ""}`}
        style={{ paddingLeft: `${depth * 14 + 26}px` }}
        onClick={() => handleSelectFile(file.path)}
        title={file.path}
      >
        {getFileIcon(file.name)}
        <span className="wfe-node-name">{file.name}</span>
        {file.size !== undefined && file.size !== null && (
          <span className="wfe-file-size">{formatBytes(file.size)}</span>
        )}
      </button>
    );
  };

  return (
    <div className="workspace-file-explorer">
      {/* Split layout: Explorer on Left, Code Viewer on Right */}
      <div className="wfe-split-container">
        {/* Left Column: File Tree */}
        <div className="wfe-tree-pane">
          <div className="wfe-tree-header">
            <div className="wfe-tree-title-group">
              <span className="wfe-tree-title">Files</span>
              <span className="wfe-file-count" title="Total files in workspace">
                {files.length}
              </span>
            </div>
            <button
              className="wfe-btn-icon"
              onClick={fetchFiles}
              disabled={isLoadingFiles}
              title="Refresh files"
              aria-label="Refresh files"
            >
              <RefreshCw size={13} className={isLoadingFiles ? "wfe-spin" : ""} />
            </button>
          </div>

          {/* Quick Filter */}
          <div className="wfe-search-box">
            <Search size={13} className="wfe-search-icon" />
            <input
              type="text"
              className="wfe-search-input"
              placeholder="Search files..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
            />
            {filterQuery && (
              <button
                className="wfe-search-clear"
                onClick={() => setFilterQuery("")}
                title="Clear filter"
              >
                ×
              </button>
            )}
          </div>

          {/* Tree Body */}
          <div className="wfe-tree-body">
            {isLoadingFiles ? (
              <div className="wfe-state-box">
                <Loader2 size={16} className="wfe-spin" />
                <span>Loading workspace files...</span>
              </div>
            ) : filesError ? (
              <div className="wfe-state-box error">
                <AlertCircle size={16} />
                <span>{filesError}</span>
                <button className="wfe-retry-btn" onClick={fetchFiles}>
                  Retry
                </button>
              </div>
            ) : files.length === 0 ? (
              <div className="wfe-state-box empty">
                <span>No files in workspace.</span>
              </div>
            ) : filteredFiles !== null ? (
              /* Search results mode */
              <div className="wfe-search-results">
                {filteredFiles.length === 0 ? (
                  <div className="wfe-state-box empty">
                    <span>No matching files.</span>
                  </div>
                ) : (
                  filteredFiles.map((file) => {
                    const isSelected = selectedFilePath === file.path;
                    return (
                      <button
                        key={file.path}
                        className={`wfe-tree-row wfe-file-row ${isSelected ? "active" : ""}`}
                        style={{ paddingLeft: "12px" }}
                        onClick={() => handleSelectFile(file.path)}
                        title={file.path}
                      >
                        {getFileIcon(file.name)}
                        <div className="wfe-filtered-path">
                          <span className="wfe-node-name">{file.name}</span>
                          <span className="wfe-node-subpath">{file.path}</span>
                        </div>
                        <span className="wfe-file-size">{formatBytes(file.size)}</span>
                      </button>
                    );
                  })
                )}
              </div>
            ) : (
              /* Hierarchical tree mode */
              <div className="wfe-tree-list">
                {Object.keys(tree.dirs)
                  .sort((a, b) => a.localeCompare(b))
                  .map((dirName) => renderDirNode(tree.dirs[dirName], 0))}
                {[...tree.files]
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map((file) => renderFileRow(file, 0))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Read-Only Code Viewer */}
        <div className="wfe-viewer-pane">
          {selectedFilePath ? (
            <div className="wfe-viewer-inner">
              {/* Viewer Header */}
              <div className="wfe-viewer-header">
                <div className="wfe-viewer-title-row">
                  {getFileIcon(selectedFilePath)}
                  <span className="wfe-viewer-filepath" title={selectedFilePath}>
                    {selectedFilePath}
                  </span>
                </div>

                <div className="wfe-viewer-badges">
                  {selectedFileContent?.language && (
                    <span className="wfe-badge lang">
                      {selectedFileContent.language}
                    </span>
                  )}
                  {selectedFileContent?.size !== undefined && (
                    <span className="wfe-badge size">
                      {formatBytes(selectedFileContent.size)}
                    </span>
                  )}
                  <span className="wfe-badge readonly">
                    <ShieldCheck size={12} />
                    <span>Read-only</span>
                  </span>
                  {selectedFileContent?.content && (
                    <button
                      className="wfe-btn-copy"
                      onClick={handleCopy}
                      title="Copy code to clipboard"
                    >
                      {copied ? (
                        <>
                          <Check size={13} color="#4ade80" />
                          <span style={{ color: "#4ade80" }}>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={13} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Viewer Content */}
              <div className="wfe-viewer-body">
                {isLoadingContent ? (
                  <div className="wfe-state-box">
                    <Loader2 size={20} className="wfe-spin" />
                    <span>Loading file content...</span>
                  </div>
                ) : contentError ? (
                  <div className="wfe-state-box error">
                    <AlertCircle size={20} />
                    <span>{contentError}</span>
                  </div>
                ) : selectedFileContent ? (
                  <div className="wfe-code-container">
                    <SyntaxHighlighter
                      language={selectedFileContent.language || "text"}
                      style={vscDarkPlus}
                      showLineNumbers={true}
                      wrapLines={false}
                      customStyle={{
                        margin: 0,
                        padding: "1rem",
                        background: "var(--color-bg-primary)",
                        fontSize: "0.85rem",
                        fontFamily:
                          'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                        lineHeight: "1.6",
                        height: "100%",
                        overflow: "auto",
                      }}
                      lineNumberStyle={{
                        color: "var(--color-text-secondary)",
                        opacity: 0.45,
                        minWidth: "2.8em",
                        paddingRight: "1em",
                        userSelect: "none",
                      }}
                    >
                      {selectedFileContent.content}
                    </SyntaxHighlighter>
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            /* Placeholder when no file is selected */
            <div className="wfe-placeholder">
              <div className="wfe-placeholder-icon">
                <Code2 size={40} />
              </div>
              <h4 className="wfe-placeholder-title">Select a file to inspect</h4>
              <p className="wfe-placeholder-desc">
                Browse the workspace directory on the left and click any file to safely
                view its source code in read-only mode.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
