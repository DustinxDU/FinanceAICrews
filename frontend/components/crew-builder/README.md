# Crew Builder - New Design Implementation

## Components
- `index.tsx` - Main entry, exports CrewBuilderNew
- `types.ts` - TypeScript definitions
- `constants.ts` - Templates
- `Toast.tsx` - Notifications
- `CrewList.tsx` - Crew list view
- `BuilderCanvas.tsx` - Visual node editor
- `NodeComponents.tsx` - Node components
- `PropertyPanels.tsx` - Config panels

## APIs Connected
- List Crews: `apiClient.listCustomCrews()`
- Create Crew: `apiClient.createCrew()`
- MCP Tools: `apiClient.listMCPTools()`

## Future Work
1. Run crew execution (backend integration)
2. Edit existing crews
3. Clone/delete crews from list
4. Knowledge source picker integration
5. Real-time task progress tracking
