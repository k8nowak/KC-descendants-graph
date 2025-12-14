"""
Interactive visualization script for KC descendance graphs with draggable nodes.

This script creates interactive HTML visualizations where users can:
- Drag nodes around to reposition them
- Zoom and pan the graph
- Hover over nodes to see details
- Click on nodes to highlight connections

Uses pyvis for interactive network visualization.
"""

import sys
import re
import networkx as nx

try:
    from pyvis.network import Network
except ImportError:
    print("Error: pyvis is required for interactive visualization.")
    print("Install it with: pip install pyvis")
    sys.exit(1)

# Import functions from the main visualization script
from visualize_kc_graph_with_neighborhood import (
    create_graph_from_csv,
    filter_isolated_nodes,
    identify_sources_and_sinks,
    create_hierarchical_layout_with_clustering,
    extract_neighborhood,
    resolve_kc_identifier
)


def visualize_descendance_graph_interactive(G, output_file='kc_descendance_graph.html', 
                                           title='Descendance Graph: KC Relationships',
                                           height='800px', width='100%'):
    """
    Create an interactive HTML visualization of the descendance graph with draggable nodes.
    Uses pyvis for interactivity.
    
    - Sources (green): KCs with no antecedents
    - Sinks (red): KCs with no descendants
    - Intermediate (blue): KCs that are neither sources nor sinks
    
    Args:
        G: NetworkX DiGraph
        output_file: Output HTML filename
        title: Graph title
        height: Height of the visualization (default '800px')
        width: Width of the visualization (default '100%')
    """
    # Filter isolated nodes
    G = filter_isolated_nodes(G)
    
    sources, sinks, intermediate = identify_sources_and_sinks(G)
    
    # Get initial layout positions (reuse the hierarchical layout)
    try:
        pos = create_hierarchical_layout_with_clustering(G)
    except Exception as e:
        print(f"Warning: Could not create hierarchical layout: {e}")
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot', args='-Grankdir=LR')
        except:
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Create pyvis network
    net = Network(
        height=height,
        width=width,
        directed=True,
        bgcolor='#ffffff',
        font_color='black',
        notebook=False
    )
    
    # Configure physics - disable it since we're providing initial positions
    # This prevents the graph from constantly drifting
    net.set_options("""
    {
      "nodes": {
        "font": {
          "size": 14,
          "face": "Arial",
          "bold": true
        },
        "borderWidth": 2
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 1.2
          }
        },
        "color": {
          "color": "#888888",
          "highlight": "#000000"
        },
        "smooth": {
          "type": "continuous",
          "roundness": 0.1
        }
      },
      "physics": {
        "enabled": false
      },
      "interaction": {
        "dragNodes": true,
        "dragView": true,
        "zoomView": true,
        "hover": true,
        "tooltipDelay": 200
      }
    }
    """)
    
    # Add nodes with color coding and initial positions
    for node in G.nodes():
        kc_number = G.nodes[node].get('number', node)
        description = G.nodes[node].get('description', '')
        in_degree = G.in_degree(node)
        out_degree = G.out_degree(node)
        
        # Tooltip shows only the short description (or KC number if no description)
        title_text = description if description else f'KC {kc_number}'
        
        # Determine node color based on type
        if node in sources:
            color = '#90EE90'  # lightgreen
            border_color = '#006400'  # darkgreen
        elif node in sinks:
            color = '#F08080'  # lightcoral
            border_color = '#8B0000'  # darkred
        else:
            color = '#87CEEB'  # lightblue
            border_color = '#00008B'  # darkblue
        
        # Get initial position from layout
        x, y = pos.get(node, (0, 0))
        
        # Scale positions for pyvis (pyvis uses different coordinate system)
        # Convert to screen coordinates (pyvis uses pixels, roughly 0-1000 range)
        scale_factor = 100
        x_scaled = x * scale_factor + 500
        y_scaled = y * scale_factor + 400
        
        # Determine node size based on degree
        node_size = 20 + (in_degree + out_degree) * 3
        node_size = min(max(node_size, 15), 50)  # Clamp between 15 and 50
        
        net.add_node(
            node,
            label=kc_number,
            title=title_text,
            color=color,
            borderWidth=2,
            borderWidthSelected=4,
            size=node_size,
            x=x_scaled,
            y=y_scaled,
            fixed={'x': False, 'y': False}  # Allow dragging
        )
    
    # Add edges with tooltips showing both node descriptions
    for edge in G.edges():
        source, target = edge
        
        # Get descriptions for both nodes, fallback to KC number if no description
        source_description = G.nodes[source].get('description', '')
        target_description = G.nodes[target].get('description', '')
        source_number = G.nodes[source].get('number', source)
        target_number = G.nodes[target].get('number', target)
        
        # Create tooltip text
        from_text = source_description if source_description else f'KC {source_number}'
        to_text = target_description if target_description else f'KC {target_number}'
        tooltip_text = f'From: {from_text}\nTo: {to_text}'
        
        net.add_edge(source, target, color='#888888', width=1, title=tooltip_text)
    
    # Save as HTML (don't set heading here to avoid duplication)
    net.save_graph(output_file)
    
    # Add title manually to HTML to ensure it only appears once
    if title:
        with open(output_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Remove any existing headings that pyvis might have added
        # Remove <h1> tags that might be in the body
        html_content = re.sub(r'<h1[^>]*>.*?</h1>', '', html_content, flags=re.DOTALL)
        
        # Find the body tag and add title right after it
        # Replace the first occurrence of <body> with <body> + title
        title_html = f'<h1 style="text-align: center; margin: 20px 0; font-family: Arial, sans-serif;">{title}</h1>'
        html_content = html_content.replace('<body>', f'<body>\n{title_html}', 1)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    print(f"Interactive descendance graph saved to {output_file}")
    print(f"Open {output_file} in a web browser to interact with the graph")
    print(f"  - Drag nodes to reposition them")
    print(f"  - Zoom with mouse wheel or pinch")
    print(f"  - Pan by dragging the background")
    print(f"  - Hover over nodes to see details")
    
    # Display statistics
    print(f"\nGraph Statistics:")
    print(f"  Total KCs: {G.number_of_nodes()}")
    print(f"  Total relationships: {G.number_of_edges()}")
    print(f"  Sources: {len(sources)}")
    print(f"  Sinks: {len(sinks)}")
    print(f"  Intermediate KCs: {len(intermediate)}")
    print(f"  Is acyclic: {nx.is_directed_acyclic_graph(G)}")


def visualize_neighborhood_interactive(G, kc_identifiers, id_to_number, number_to_id, 
                                      output_file='kc_neighborhood.html',
                                      height='800px', width='100%'):
    """
    Visualize the neighborhood of one or more KCs interactively.
    
    Args:
        G: The full descendance graph
        kc_identifiers: List of KC identifiers (Numbers or IDs) or single identifier
        id_to_number: Mapping from KC ID to Number
        number_to_id: Mapping from KC Number to ID
        output_file: Output filename for the visualization
        height: Height of the visualization
        width: Width of the visualization
    """
    if not isinstance(kc_identifiers, list):
        kc_identifiers = [kc_identifiers]
    
    # Resolve identifiers to node IDs
    kc_nodes = []
    resolved_numbers = []
    for identifier in kc_identifiers:
        node_id = resolve_kc_identifier(identifier, number_to_id, id_to_number)
        if node_id:
            kc_nodes.append(node_id)
            resolved_numbers.append(id_to_number.get(node_id, node_id))
        else:
            print(f"Warning: Could not find KC '{identifier}'")
    
    if not kc_nodes:
        print("Error: No valid KCs found. Cannot create neighborhood visualization.")
        return
    
    # Extract neighborhood
    neighborhood_G = extract_neighborhood(G, kc_nodes, id_to_number)
    
    if neighborhood_G.number_of_nodes() == 0:
        print("Error: Neighborhood is empty.")
        return
    
    # Create title
    if len(resolved_numbers) == 1:
        title = f'Neighborhood of KC {resolved_numbers[0]}'
    else:
        title = f'Neighborhood of KCs: {", ".join(resolved_numbers)}'
    
    # Visualize the neighborhood
    visualize_descendance_graph_interactive(
        neighborhood_G, 
        output_file=output_file,
        title=title,
        height=height,
        width=width
    )
    
    print(f"\nNeighborhood includes {neighborhood_G.number_of_nodes()} KCs and "
          f"{neighborhood_G.number_of_edges()} relationships.")


def main():
    """
    Main function to create and visualize interactive descendance graphs from CSV.
    
    Command-line usage:
        python visualize_kc_graph_interactive.py [csv_file] [option] [kc1] [kc2] ...
    
    Arguments:
        csv_file: Optional CSV file path (default: 'Counting Numbers KCs Nov 2025.csv')
        option: 1 for full graph, 2 for neighborhood (if omitted, runs interactively)
        kc1, kc2, ...: KC identifiers for option 2 (Numbers or IDs, space-separated)
    
    Examples:
        python visualize_kc_graph_interactive.py
            # Interactive mode - prompts for options
        
        python visualize_kc_graph_interactive.py 1
            # Generate full graph
        
        python visualize_kc_graph_interactive.py 2 411 701
            # Generate neighborhood for KCs 411 and 701
        
        python visualize_kc_graph_interactive.py my_file.csv 2 411 701
            # Use custom CSV file and generate neighborhood
    """
    # Parse command-line arguments
    args = sys.argv[1:]
    
    # Determine CSV file (first arg if it's a .csv file, otherwise use default)
    csv_file = 'Counting Numbers KCs Nov 2025.csv'
    option = None
    kc_identifiers = []
    
    if len(args) > 0:
        # Check if first argument is a CSV file
        if args[0].endswith('.csv'):
            csv_file = args[0]
            args = args[1:]
        
        # Check if first remaining arg is an option (1 or 2)
        if len(args) > 0 and args[0] in ['1', '2']:
            option = args[0]
            # Remaining args are KC identifiers
            kc_identifiers = args[1:] if len(args) > 1 else []
        elif len(args) > 0:
            # First arg might be option without CSV specified
            if args[0] in ['1', '2']:
                option = args[0]
                kc_identifiers = args[1:] if len(args) > 1 else []
    
    print(f"Reading KC data from: {csv_file}")
    
    G, id_to_number, _ = create_graph_from_csv(csv_file)
    
    # Get number_to_id mapping for resolving identifiers
    number_to_id = {v: k for k, v in id_to_number.items()}
    
    # If no option specified, run interactively
    if option is None:
        print("\n" + "="*60)
        print("Interactive KC Descendance Graph Visualization")
        print("="*60)
        print("What would you like to visualize?")
        print("1. Full descendance graph (Interactive HTML)")
        print("2. Neighborhood of specific KC(s) (Interactive HTML)")
        print("="*60)
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == '2':
            print("\nEnter KC identifier(s) (Number or ID).")
            print("For multiple KCs, separate with commas (e.g., '1.1, 1.2' or 'KC1, KC2')")
            kc_input = input("KC(s): ").strip()
            
            # Parse input (handle comma-separated list)
            kc_identifiers = [kc.strip() for kc in kc_input.split(',')]
        else:
            option = '1'
            kc_identifiers = []
    else:
        # Use command-line provided KCs
        kc_identifiers = kc_identifiers if kc_identifiers else []
    
    # Execute the chosen option
    if option == '2':
        if not kc_identifiers:
            print("Error: Option 2 requires at least one KC identifier.")
            print("Usage: python visualize_kc_graph_interactive.py [csv_file] 2 <kc1> [kc2] ...")
            return
        
        # Generate output filename based on KC numbers
        resolved_ids = []
        for identifier in kc_identifiers:
            node_id = resolve_kc_identifier(identifier, number_to_id, id_to_number)
            if node_id:
                resolved_ids.append(id_to_number.get(node_id, node_id))
        
        if resolved_ids:
            filename = f"kc_neighborhood_{'_'.join(resolved_ids).replace('.', '_')}.html"
        else:
            filename = 'kc_neighborhood.html'
        
        visualize_neighborhood_interactive(
            G, kc_identifiers, id_to_number, number_to_id, 
            output_file=filename
        )
    else:
        # Option 1: visualize full graph
        visualize_descendance_graph_interactive(
            G, 
            output_file='kc_descendance_graph.html',
            title='Descendance Graph: Counting Numbers KCs'
        )


if __name__ == '__main__':
    main()

