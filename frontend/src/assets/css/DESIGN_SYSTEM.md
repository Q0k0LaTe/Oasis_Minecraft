# CSS Design System Documentation

## Design Principles

This design system follows Claude's style of simplicity, warmth, and modern design:

1. **Simplicity**: Keep interfaces clean and avoid unnecessary decoration
2. **Warmth**: Use warm color tones to create a friendly user experience
3. **Consistency**: Unified spacing, color, and typography systems
4. **Accessibility**: Ensure good contrast and focus states

## Color System

### Primary Colors

```css
/* Background Colors - Warm Beige */
--bg-primary: #fefcf9;        /* Primary background, warm and soft */
--bg-secondary: #faf8f5;      /* Secondary background (reserve) */

/* Text Colors */
--text-primary: #1a1a1a;      /* Primary text color */
--text-secondary: #4a4a4a;    /* Secondary text color */
--text-muted: #8a8a8a;        /* Muted text color */

/* Accent Colors - Orange Palette */
--accent-primary: #ff6b35;    /* Primary accent, for buttons, links, etc. */
--accent-hover: #ff8552;      /* Hover state */
--accent-active: #e55a2b;     /* Active state (optional) */
```

### Usage Guidelines

- **Background Colors**: Use `--bg-primary` for pages and containers
- **Accent Colors**: Use `--accent-primary` for interactive elements (buttons, links, focus)
- **Text Colors**: Choose `--text-primary`, `--text-secondary`, or `--text-muted` based on importance

## Typography System

### Font Family

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
  'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
```

Uses system font stack to ensure cross-platform consistency and performance.

### Font Sizes

```css
/* Headings */
--font-size-h1: 2rem;         /* 32px - Page main heading */
--font-size-h2: 1.5rem;       /* 24px - Section heading */
--font-size-h3: 1.25rem;      /* 20px - Subsection heading */

/* Body Text */
--font-size-base: 1rem;       /* 16px - Body text */
--font-size-small: 0.875rem;  /* 14px - Auxiliary text */
--font-size-xs: 0.75rem;      /* 12px - Labels, captions */
```

### Font Weights

```css
--font-weight-normal: 400;    /* Body text */
--font-weight-medium: 500;    /* Buttons, emphasized text */
--font-weight-semibold: 600;  /* Headings */
--font-weight-bold: 700;      /* Important headings (use sparingly) */
```

### Letter Spacing

```css
--letter-spacing-tight: -0.02em;   /* Headings */
--letter-spacing-normal: -0.01em;  /* Buttons */
--letter-spacing-wide: 0;          /* Body text */
```

## Spacing System

Uses multiples of 8px base unit (0.5rem):

```css
/* Spacing Units */
--spacing-xs: 0.25rem;    /* 4px */
--spacing-sm: 0.5rem;     /* 8px */
--spacing-md: 0.75rem;    /* 12px */
--spacing-base: 1rem;     /* 16px */
--spacing-lg: 1.5rem;     /* 24px */
--spacing-xl: 2rem;       /* 32px */
--spacing-2xl: 3rem;      /* 48px */
--spacing-3xl: 4rem;      /* 64px */
```

### Usage Guidelines

- **Internal Component Spacing**: Use `--spacing-sm` to `--spacing-md`
- **Between Components**: Use `--spacing-base` to `--spacing-lg`
- **Section Spacing**: Use `--spacing-xl` to `--spacing-2xl`

## Border Radius System

```css
--radius-sm: 4px;      /* Small elements */
--radius-md: 8px;      /* Buttons, cards */
--radius-lg: 12px;     /* Large cards, modals */
--radius-full: 9999px; /* Circular elements */
```

## Shadow System

```css
/* Shadows */
--shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.15);

/* Accent Shadows (for orange elements) */
--shadow-accent-sm: 0 2px 6px rgba(255, 107, 53, 0.2);
--shadow-accent-md: 0 4px 12px rgba(255, 107, 53, 0.3);
--shadow-accent-lg: 0 8px 24px rgba(255, 107, 53, 0.4);
```

## Transition Animations

```css
--transition-fast: 0.15s ease;
--transition-base: 0.2s ease;
--transition-slow: 0.3s ease;
```

## Component Style Guidelines

### Button

```css
/* Primary Button */
.button-primary {
  padding: 0.875rem 1.5rem;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: #ffffff;
  background-color: var(--accent-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  letter-spacing: var(--letter-spacing-normal);
}

.button-primary:hover {
  background-color: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent-md);
}

.button-primary:active {
  transform: translateY(0);
  box-shadow: var(--shadow-accent-sm);
}

.button-primary:focus {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
```

### Container

```css
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--spacing-xl);
  background-color: var(--bg-primary);
}
```

### Heading

```css
.headline {
  font-size: var(--font-size-h1);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xl);
  text-align: center;
  letter-spacing: var(--letter-spacing-tight);
}
```

## Responsive Design

### Breakpoints

```css
/* Mobile First */
--breakpoint-sm: 640px;   /* Small screens */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Desktop */
--breakpoint-xl: 1280px;  /* Large desktop */
```

### Usage Example

```css
@media (min-width: 768px) {
  .container {
    padding: var(--spacing-2xl);
  }
  
  .headline {
    font-size: 2.5rem;
  }
}
```

## Accessibility

### Focus States

All interactive elements must include clear focus states:

```css
.element:focus {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
```

### Contrast

- Text to background contrast ratio of at least 4.5:1 (WCAG AA)
- Large text (18px+) at least 3:1

## Usage Examples

### Creating New Components

1. **Identify Component Type**: Button, card, input field, etc.
2. **Choose Colors**: Use color variables from the design system
3. **Apply Spacing**: Use spacing system to maintain consistency
4. **Add Interactive States**: hover, active, focus
5. **Test Accessibility**: Ensure contrast and focus states

### Example: Card Component

```css
.card {
  background-color: var(--bg-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-base);
}

.card:hover {
  box-shadow: var(--shadow-md);
}

.card-title {
  font-size: var(--font-size-h2);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-base);
}

.card-content {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  line-height: 1.6;
}
```

## Maintenance Guidelines

1. **Maintain Consistency**: New components should follow this design system
2. **Use Variables**: Prefer CSS variables over hardcoded values
3. **Update Documentation**: Update this document when adding new components
4. **Code Review**: Ensure new code follows design specifications

## Future Expansion Directions

- [ ] Convert design system to CSS variables file
- [ ] Add dark mode support
- [ ] Create component library documentation
- [ ] Add more component styles (input fields, dropdowns, etc.)
