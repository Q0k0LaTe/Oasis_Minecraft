/**
 * SpecEditor - Modal for manually editing the spec JSON
 */

import React, { useState, useEffect } from 'react';

export default function SpecEditor({
  spec,
  onSave,
  onClose,
}) {
  const [jsonText, setJsonText] = useState('');
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Initialize with current spec
  useEffect(() => {
    if (spec) {
      setJsonText(JSON.stringify(spec, null, 2));
    }
  }, [spec]);

  // Track changes
  const handleChange = (e) => {
    setJsonText(e.target.value);
    setIsDirty(true);
    setError(null);
  };

  // Validate and save
  const handleSave = async () => {
    setError(null);

    // Parse JSON
    let parsedSpec;
    try {
      parsedSpec = JSON.parse(jsonText);
    } catch (err) {
      setError(`Invalid JSON: ${err.message}`);
      return;
    }

    // Basic validation
    if (!parsedSpec.mod_name) {
      setError('Spec must have a mod_name');
      return;
    }
    if (!parsedSpec.mod_id) {
      setError('Spec must have a mod_id');
      return;
    }

    setIsSaving(true);
    try {
      const result = await onSave(parsedSpec);
      if (result.success) {
        setIsDirty(false);
        onClose();
      } else {
        setError(result.error || 'Failed to save spec');
      }
    } catch (err) {
      setError(err.message || 'Failed to save spec');
    } finally {
      setIsSaving(false);
    }
  };

  // Format JSON
  const handleFormat = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
      setError(null);
    } catch (err) {
      setError(`Cannot format - invalid JSON: ${err.message}`);
    }
  };

  // Handle close with unsaved changes
  const handleClose = () => {
    if (isDirty) {
      if (confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose();
      }
    } else {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal spec-editor-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Spec</h2>
          <div className="modal-header-actions">
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleFormat}
              disabled={isSaving}
            >
              Format
            </button>
            <button className="btn btn-icon btn-ghost" onClick={handleClose} disabled={isSaving}>
              ×
            </button>
          </div>
        </div>

        <div className="modal-body">
          <div className="editor-info">
            <p>
              Edit the mod specification JSON directly. Changes will be saved when you click Save.
            </p>
          </div>

          <div className="editor-container">
            <textarea
              className={`spec-editor-textarea ${error ? 'has-error' : ''}`}
              value={jsonText}
              onChange={handleChange}
              spellCheck={false}
              disabled={isSaving}
            />
            <div className="editor-line-numbers">
              {jsonText.split('\n').map((_, i) => (
                <div key={i} className="line-number">{i + 1}</div>
              ))}
            </div>
          </div>

          {error && (
            <div className="editor-error">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <div className="footer-left">
            {isDirty && <span className="unsaved-indicator">Unsaved changes</span>}
          </div>
          <div className="footer-right">
            <button
              className="btn btn-ghost"
              onClick={handleClose}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={isSaving || !isDirty}
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

