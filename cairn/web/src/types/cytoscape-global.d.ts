declare module 'cytoscape' {
  const value: unknown;
  export default value;
}

declare global {
  interface Window {
    cytoscape?: any;
    cytoscapeDagre?: any;
    cytoscapeKlay?: any;
    cytoscapeElk?: any;
    ELK?: any;
    klay?: any;
  }
}

export {};
