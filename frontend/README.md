# DocLens Frontend

Next.js 15 frontend for the DocLens document analyzer application.

## Features

- 📤 **Drag & Drop Upload**: Modern file upload with visual feedback
- ⚡ **Real-time Processing**: Live status updates during analysis
- 🎨 **Beautiful UI**: Dark theme with gradient accents and animations
- 📋 **JSON Viewer**: Syntax-highlighted, collapsible result display
- 📱 **Responsive**: Works on desktop, tablet, and mobile

## Tech Stack

- **Next.js** 15 - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **React** 19 - Component library

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure API URL (Optional)

By default, the frontend connects to `http://localhost:8000`. To change this:

```bash
# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://your-api-url" > .env.local
```

### 3. Start Development Server

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main page component
│   │   ├── layout.tsx        # Root layout
│   │   └── globals.css       # Global styles
│   ├── components/
│   │   ├── UploadBox.tsx     # File upload component
│   │   ├── ActionForm.tsx    # Action selection form
│   │   ├── JsonViewer.tsx    # Result viewer
│   │   └── LimitsNotice.tsx  # Usage limits panel
│   └── lib/
│       └── api.ts            # API client
├── public/                   # Static assets
├── next.config.ts            # Next.js configuration
├── tailwind.config.ts        # Tailwind configuration
└── package.json
```

## Components

### UploadBox
Handles file uploads with drag-and-drop support:
- Client-side file type validation
- Size limit checking
- Visual feedback during upload
- Displays uploaded file metadata

### ActionForm
Action selection and configuration:
- 5 analysis actions (summarize, extract, classify, QA, transform)
- Conditional fields (question for QA, format for transform)
- Refinement instructions textarea

### JsonViewer
Displays analysis results:
- Syntax-highlighted JSON tree
- Collapsible sections
- One-click copy to clipboard

### LimitsNotice
Shows usage information:
- File size limits
- Rate limiting status
- Expandable details panel

## Available Scripts

```bash
# Development
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## API Integration

The frontend communicates with the backend via these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload a document |
| `/api/run` | POST | Run an analysis action |
| `/api/job/{id}` | GET | Get job status/result |

See `src/lib/api.ts` for the full API client implementation.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

## Styling

The app uses Tailwind CSS with a custom dark theme:

- **Background**: Slate 950 (#020817)
- **Primary**: Violet/Fuchsia gradient
- **Success**: Emerald
- **Error**: Red
- **Text**: White/Slate shades

Custom scrollbars and focus styles are defined in `globals.css`.

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
