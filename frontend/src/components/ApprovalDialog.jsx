/**
 * ApprovalDialog - Modal for reviewing and approving/rejecting spec deltas
 * 
 * This dialog is shown when the run enters 'awaiting_approval' state.
 * Users MUST click Approve or Reject to continue the workflow.
 */

import React, { useState } from 'react';

export default function ApprovalDialog({
  deltas,
  onApprove,
  onReject,
  onClose,
}) {
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      await onApprove();
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!showRejectInput) {
      setShowRejectInput(true);
      return;
    }
    
    setIsProcessing(true);
    try {
      await onReject(rejectReason || null);
    } finally {
      setIsProcessing(false);
    }
  };

  const getOperationIcon = (op) => {
    switch (op?.toLowerCase()) {
      case 'add': return '➕';
      case 'update': return '✏️';
      case 'delete': return '🗑️';
      case 'remove': return '🗑️';
      default: return '📝';
    }
  };

  const getOperationClass = (op) => {
    switch (op?.toLowerCase()) {
      case 'add': return 'add';
      case 'update': return 'update';
      case 'delete': return 'delete';
      case 'remove': return 'delete';
      default: return 'default';
    }
  };

  const deltasCount = deltas?.length || 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal approval-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Review Changes ({deltasCount})</h2>
          <button className="btn btn-icon btn-ghost" onClick={onClose} disabled={isProcessing}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {deltasCount > 0 ? (
            <>
              <p className="approval-intro">
                The AI has proposed {deltasCount} change{deltasCount !== 1 ? 's' : ''} to your mod spec.
                Review them and approve or reject.
              </p>
              <div className="deltas-list">
                {deltas.map((delta, index) => (
                  <div key={index} className={`delta-item ${getOperationClass(delta.operation)}`}>
                    <div className="delta-header">
                      <span className="delta-icon">{getOperationIcon(delta.operation)}</span>
                      <span className="delta-operation">{delta.operation || 'change'}</span>
                      <span className="delta-path">{delta.path || 'spec'}</span>
                    </div>
                    
                    {delta.value !== undefined && (
                      <div className="delta-value">
                        <pre>{JSON.stringify(delta.value, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="deltas-empty">
              <div className="empty-icon">✨</div>
              <p className="empty-title">No changes needed</p>
              <p className="empty-description">
                The AI analyzed your request but didn't generate any spec changes.
                This might mean:
              </p>
              <ul className="empty-reasons">
                <li>Your mod spec already has what you described</li>
                <li>The request was unclear - try being more specific</li>
                <li>The feature isn't supported yet</li>
              </ul>
              <p className="empty-action">
                Click <strong>Approve</strong> to continue, or <strong>Reject</strong> to try a different prompt.
              </p>
            </div>
          )}

          {showRejectInput && (
            <div className="reject-reason">
              <label htmlFor="reject-reason">Reason for rejection (optional)</label>
              <textarea
                id="reject-reason"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Explain why you're rejecting these changes..."
                rows={3}
                disabled={isProcessing}
              />
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-ghost"
            onClick={onClose}
            disabled={isProcessing}
          >
            Cancel
          </button>
          <button
            className="btn btn-danger"
            onClick={handleReject}
            disabled={isProcessing}
          >
            {showRejectInput ? 'Confirm Reject' : 'Reject'}
          </button>
          <button
            className="btn btn-success"
            onClick={handleApprove}
            disabled={isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Approve'}
          </button>
        </div>
      </div>
    </div>
  );
}

