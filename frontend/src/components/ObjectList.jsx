/**
 * ObjectList - Left column component showing grouped objects from spec
 * Groups: Block / Item / Structure (tools)
 */

import React, { useMemo } from 'react';

export default function ObjectList({
  spec,
  selectedObject,
  onSelectObject,
  onDeleteObject,
  onExport,
  onBuild,
  isBuildRunning,
}) {
  // Extract objects from spec
  const objects = useMemo(() => {
    if (!spec) return { blocks: [], items: [], structures: [] };
    return {
      blocks: spec.blocks || [],
      items: spec.items || [],
      structures: spec.tools || spec.structures || [],
    };
  }, [spec]);

  const hasObjects = objects.blocks.length > 0 || 
                     objects.items.length > 0 || 
                     objects.structures.length > 0;

  return (
    <div className="object-list">
      <div className="object-list-content">
        {/* Block Section */}
        <ObjectSection
          title="Block"
          objects={objects.blocks}
          type="block"
          selectedObject={selectedObject}
          onSelect={onSelectObject}
          onDelete={onDeleteObject}
          emptyText="No blocks defined"
        />

        {/* Item Section */}
        <ObjectSection
          title="Item"
          objects={objects.items}
          type="item"
          selectedObject={selectedObject}
          onSelect={onSelectObject}
          onDelete={onDeleteObject}
          emptyText="No items defined"
        />

        {/* Structure/Tools Section */}
        <ObjectSection
          title="Structure"
          objects={objects.structures}
          type="structure"
          selectedObject={selectedObject}
          onSelect={onSelectObject}
          onDelete={onDeleteObject}
          emptyText="No structures defined"
        />

        {!hasObjects && (
          <div className="object-list-empty">
            <p>No objects yet</p>
            <p className="hint">Send a message to create items, blocks, or tools!</p>
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      <div className="object-list-actions">
        <button
          className="btn btn-secondary btn-block"
          onClick={onExport}
          disabled={!spec}
        >
          Export
        </button>
        <button
          className="btn btn-primary btn-block"
          onClick={onBuild}
          disabled={isBuildRunning || !hasObjects}
        >
          {isBuildRunning ? 'Building...' : 'Build'}
        </button>
      </div>
    </div>
  );
}

/**
 * ObjectSection - A collapsible section of objects
 */
function ObjectSection({
  title,
  objects,
  type,
  selectedObject,
  onSelect,
  onDelete,
  emptyText,
}) {
  const [isExpanded, setIsExpanded] = React.useState(true);

  const getObjectName = (obj) => {
    return obj.item_name || obj.block_name || obj.tool_name || obj.name || obj.id || 'Unnamed';
  };

  const getObjectId = (obj) => {
    return obj.item_id || obj.block_id || obj.tool_id || obj.id;
  };

  const isSelected = (obj) => {
    if (!selectedObject) return false;
    return getObjectId(obj) === getObjectId(selectedObject);
  };

  const handleDelete = (e, obj, index) => {
    e.stopPropagation();
    if (onDelete) {
      onDelete(obj, type, index);
    }
  };

  return (
    <div className="object-section">
      <div
        className="object-section-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="section-title">{title}</span>
        <span className="section-count">{objects.length}</span>
        <span className={`section-toggle ${isExpanded ? 'expanded' : ''}`}>
          ▼
        </span>
      </div>

      {isExpanded && (
        <div className="object-section-content">
          {objects.length === 0 ? (
            <div className="section-empty">{emptyText}</div>
          ) : (
            objects.map((obj, index) => (
              <div
                key={getObjectId(obj) || index}
                className={`object-item ${isSelected(obj) ? 'selected' : ''}`}
                onClick={() => onSelect(obj, type)}
              >
                <span className="object-name">{getObjectName(obj)}</span>
                {obj.rarity && (
                  <span className={`object-rarity rarity-${obj.rarity.toLowerCase()}`}>
                    {obj.rarity}
                  </span>
                )}
                <button
                  className="btn-delete"
                  onClick={(e) => handleDelete(e, obj, index)}
                  title="Delete"
                >
                  <span className="delete-icon">X</span>
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

