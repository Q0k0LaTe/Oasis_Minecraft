/**
 * TextureSelectionDialog - Modal for selecting texture variants
 *
 * This dialog is shown when the run enters 'awaiting_texture_selection' state.
 * Users must select one texture variant for each item/block/tool.
 */

import React, { useState, useCallback } from 'react';

export default function TextureSelectionDialog({
  pendingTextures,
  onSelectTexture,
  onClose,
}) {
  const [selectedVariants, setSelectedVariants] = useState({});
  const [submittingEntity, setSubmittingEntity] = useState(null);
  const [completedEntities, setCompletedEntities] = useState(new Set());

  // Get list of entity IDs that still need selection
  const entityIds = Object.keys(pendingTextures || {});
  const remainingCount = entityIds.length - completedEntities.size;

  const handleVariantSelect = useCallback(async (entityId, variantIndex) => {
    // Update local selection state
    setSelectedVariants(prev => ({
      ...prev,
      [entityId]: variantIndex
    }));
  }, []);

  const handleConfirmSelection = useCallback(async (entityId) => {
    const variantIndex = selectedVariants[entityId];
    if (variantIndex === undefined) return;

    setSubmittingEntity(entityId);
    try {
      await onSelectTexture(entityId, variantIndex);
      setCompletedEntities(prev => new Set([...prev, entityId]));
    } catch (error) {
      console.error('Failed to select texture:', error);
    } finally {
      setSubmittingEntity(null);
    }
  }, [selectedVariants, onSelectTexture]);

  const getEntityTypeIcon = (entityType) => {
    switch (entityType?.toLowerCase()) {
      case 'block': return '🧱';
      case 'tool': return '🔧';
      default: return '✨';
    }
  };

  if (entityIds.length === 0) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal texture-selection-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Select Textures ({remainingCount} remaining)</h2>
          <button className="btn btn-icon btn-ghost" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <p className="texture-intro">
            The AI has generated texture variants for your mod items.
            Click on your preferred texture for each item, then confirm your selection.
          </p>

          <div className="texture-entities-list">
            {entityIds.map((entityId) => {
              const entity = pendingTextures[entityId];
              const isCompleted = completedEntities.has(entityId);
              const isSubmitting = submittingEntity === entityId;
              const selectedVariant = selectedVariants[entityId];

              if (isCompleted) {
                return (
                  <div key={entityId} className="texture-entity completed">
                    <div className="entity-header">
                      <span className="entity-icon">{getEntityTypeIcon(entity.entity_type)}</span>
                      <span className="entity-name">{entity.name || entityId}</span>
                      <span className="entity-status">✓ Selected</span>
                    </div>
                  </div>
                );
              }

              return (
                <div key={entityId} className="texture-entity">
                  <div className="entity-header">
                    <span className="entity-icon">{getEntityTypeIcon(entity.entity_type)}</span>
                    <span className="entity-name">{entity.name || entityId}</span>
                    <span className="entity-type">{entity.entity_type || 'item'}</span>
                  </div>

                  {entity.description && (
                    <p className="entity-description">{entity.description}</p>
                  )}

                  <div className="texture-variants">
                    {entity.variants?.map((variantB64, index) => (
                      <div
                        key={index}
                        className={`texture-variant ${selectedVariant === index ? 'selected' : ''}`}
                        onClick={() => handleVariantSelect(entityId, index)}
                      >
                        <div className="variant-image-container">
                          <img
                            src={`data:image/png;base64,${variantB64}`}
                            alt={`Variant ${index + 1}`}
                            className="variant-image"
                          />
                        </div>
                        <span className="variant-label">Option {index + 1}</span>
                      </div>
                    ))}
                  </div>

                  <div className="entity-actions">
                    <button
                      className="btn btn-primary"
                      onClick={() => handleConfirmSelection(entityId)}
                      disabled={selectedVariant === undefined || isSubmitting}
                    >
                      {isSubmitting ? 'Selecting...' : 'Confirm Selection'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="modal-footer">
          <p className="texture-footer-info">
            Select a texture variant for each item to continue the build.
          </p>
        </div>
      </div>
    </div>
  );
}
