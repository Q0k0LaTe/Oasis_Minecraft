/**
 * PropertiesPanel - Center column showing selected object properties
 */

import React from 'react';

export default function PropertiesPanel({
  object,
  objectType,
  onAdjust,
}) {
  if (!object) {
    return (
      <div className="properties-panel empty">
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No object selected</h3>
          <p>Select an item, block, or structure from the list to view its properties</p>
        </div>
      </div>
    );
  }

  // Get display name and ID
  const getName = () => object.item_name || object.block_name || object.tool_name || object.name || 'Unnamed';
  const getId = () => object.item_id || object.block_id || object.tool_id || object.id || 'unknown';

  // Categorize properties
  const basicProps = [];
  const advancedProps = [];

  Object.entries(object).forEach(([key, value]) => {
    // Skip internal/id fields for main display
    if (key.endsWith('_name') || key.endsWith('_id') || key === 'name' || key === 'id') {
      return;
    }

    const prop = { key, value };

    // Categorize common properties as basic
    const basicKeys = ['rarity', 'description', 'max_stack_size', 'durability', 'fireproof', 'food', 'damage'];
    if (basicKeys.includes(key)) {
      basicProps.push(prop);
    } else {
      advancedProps.push(prop);
    }
  });

  return (
    <div className="properties-panel">
      {/* Header with image placeholder */}
      <div className="properties-header">
        <div className="object-preview">
          <div className="preview-image">
            {objectType === 'block' ? '🧱' : objectType === 'structure' ? '🔧' : '✨'}
          </div>
        </div>
        <div className="object-title">
          <h2>{getName()}</h2>
          <span className="object-id">{getId()}</span>
          <span className="object-type">{objectType}</span>
        </div>
      </div>

      {/* Properties List */}
      <div className="properties-content">
        {basicProps.length > 0 && (
          <div className="properties-section">
            <h3>Properties</h3>
            <div className="properties-list">
              {basicProps.map(({ key, value }) => (
                <PropertyRow key={key} name={key} value={value} />
              ))}
            </div>
          </div>
        )}

        {advancedProps.length > 0 && (
          <div className="properties-section">
            <h3>Advanced</h3>
            <div className="properties-list">
              {advancedProps.map(({ key, value }) => (
                <PropertyRow key={key} name={key} value={value} />
              ))}
            </div>
          </div>
        )}

        {basicProps.length === 0 && advancedProps.length === 0 && (
          <div className="properties-empty">
            <p>No additional properties</p>
          </div>
        )}
      </div>

      {/* Adjust Button */}
      <div className="properties-actions">
        <button className="btn btn-secondary btn-block" onClick={onAdjust}>
          Adjust
        </button>
      </div>
    </div>
  );
}

/**
 * PropertyRow - Single property display
 */
function PropertyRow({ name, value }) {
  // Format the property name (snake_case to Title Case)
  const formatName = (str) => {
    return str
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Format the value for display
  const formatValue = (val) => {
    if (val === null || val === undefined) {
      return <span className="value-null">—</span>;
    }
    if (typeof val === 'boolean') {
      return <span className={`value-bool ${val ? 'true' : 'false'}`}>{val ? 'Yes' : 'No'}</span>;
    }
    if (typeof val === 'number') {
      return <span className="value-number">{val}</span>;
    }
    if (typeof val === 'object') {
      return <span className="value-object">{JSON.stringify(val)}</span>;
    }
    // Check for rarity
    if (name === 'rarity') {
      return <span className={`value-rarity rarity-${val.toLowerCase()}`}>{val}</span>;
    }
    return <span className="value-string">{String(val)}</span>;
  };

  return (
    <div className="property-row">
      <span className="property-name">{formatName(name)}</span>
      <span className="property-value">{formatValue(value)}</span>
    </div>
  );
}

