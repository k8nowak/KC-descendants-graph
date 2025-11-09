"""
Script to create and visualize a descendance graph from a CSV file of KCs.

A descendance graph shows:
- KCs (Knowledge Components) as nodes
- Antecedent/descendant relationships as directed edges
- Sources (KCs with no antecedents) in green
- Sinks (KCs with no descendants) in red
- Intermediate KCs in blue

This version includes functionality to visualize neighborhoods of specific KCs.
"""

import csv
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def read_kc_csv(csv_file):
    """
    Read KC data from CSV file.
    
    Returns:
        tuple: (number_to_id_map, id_to_number_map, relationships, id_to_description_map)
            - number_to_id_map: dict mapping KC numbers to full IDs
            - id_to_number_map: dict mapping KC IDs to their Number attribute
            - relationships: list of (antecedent_id, descendant_id) tuples
            - id_to_description_map: dict mapping KC IDs to their Short Description
    """
    number_to_id = {}
    id_to_number = {}
    id_to_description = {}
    kc_data = []
    
    # First pass: build mappings
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            kc_id = row['ID'].strip()
            kc_number = row['Number'].strip()
            antecedents_str = row['Antecedents'].strip()
            short_description = row.get('Short Description', '').strip()
            
            if kc_number:
                number_to_id[kc_number] = kc_id
            if kc_id and kc_number:
                id_to_number[kc_id] = kc_number
            if kc_id and short_description:
                id_to_description[kc_id] = short_description
            
            kc_data.append({
                'id': kc_id,
                'number': kc_number,
                'antecedents': antecedents_str
            })
    
    # Second pass: create relationships
    relationships = []
    for kc in kc_data:
        if kc['antecedents']:
            antecedent_numbers = [num.strip() for num in kc['antecedents'].split(',')]
            for ant_num in antecedent_numbers:
                if ant_num and ant_num in number_to_id:
                    relationships.append((number_to_id[ant_num], kc['id']))
                elif ant_num:
                    print(f"Warning: Antecedent number '{ant_num}' for KC '{kc['id']}' not found in data")
    
    return number_to_id, id_to_number, relationships, id_to_description


def create_graph_from_csv(csv_file):
    """
    Create a NetworkX directed graph from CSV data.
    
    Returns:
        tuple: (G, id_to_number_map, id_to_description_map)
    """
    G = nx.DiGraph()
    number_to_id, id_to_number, relationships, id_to_description = read_kc_csv(csv_file)
    
    # Add nodes with Number and Description attributes
    for kc_id in number_to_id.values():
        G.add_node(kc_id, 
                  number=id_to_number.get(kc_id, ''),
                  description=id_to_description.get(kc_id, ''))
    
    G.add_edges_from(relationships)
    return G, id_to_number, id_to_description


def filter_isolated_nodes(G):
    """Remove nodes that have no antecedents and no descendants."""
    isolated = [node for node in G.nodes() 
                if G.in_degree(node) == 0 and G.out_degree(node) == 0]
    
    if isolated:
        G_filtered = G.copy()
        G_filtered.remove_nodes_from(isolated)
        print(f"Removed {len(isolated)} isolated KCs (no antecedents and no descendants)")
        return G_filtered
    return G


def identify_sources_and_sinks(G):
    """Identify sources (no incoming edges) and sinks (no outgoing edges)."""
    sources = [node for node in G.nodes() if G.in_degree(node) == 0]
    sinks = [node for node in G.nodes() if G.out_degree(node) == 0]
    intermediate = [node for node in G.nodes() 
                    if node not in sources and node not in sinks]
    return sources, sinks, intermediate


def build_layers(G):
    """Build layer assignments for nodes using topological sort."""
    layers = {}
    for node in nx.topological_sort(G):
        layers[node] = 0 if G.in_degree(node) == 0 else max(layers[pred] for pred in G.predecessors(node)) + 1
    return layers


def group_by_parents(nodes, G):
    """Group nodes by their parent sets (siblings share the same parents)."""
    parent_groups = {}
    for node in nodes:
        parents = tuple(sorted(G.predecessors(node)))
        parent_groups.setdefault(parents, []).append(node)
    return parent_groups


def create_hierarchical_layout_with_clustering(G):
    """
    Create a hierarchical layout that clusters siblings (nodes with same antecedents)
    with tight vertical grouping and minimal edge crossings.
    
    Returns:
        dict: node -> (x, y) position mapping
    """
    layers = build_layers(G)
    
    # Group nodes by layer
    layer_nodes = {}
    for node, layer in layers.items():
        layer_nodes.setdefault(layer, []).append(node)
    
    pos = {}
    max_layer = max(layers.values()) if layers else 0
    num_nodes = G.number_of_nodes()
    
    # Scale spacing based on graph size - smaller graphs get tighter spacing
    if num_nodes <= 10:
        # Very small graphs: compact spacing
        base_x_spacing = 2.0
        min_group_spacing = 1.0
        sibling_spacing = 0.4
    elif num_nodes <= 25:
        # Small graphs: moderate spacing
        base_x_spacing = 2.5
        min_group_spacing = 1.5
        sibling_spacing = 0.45
    else:
        # Larger graphs: original spacing
        base_x_spacing = 4.0
        min_group_spacing = 2.5
        sibling_spacing = 0.5
    
    x_spacing = max(base_x_spacing, 25 / (max_layer + 1)) if max_layer > 0 else base_x_spacing
    
    # Process layers from left to right
    for layer in sorted(layer_nodes.keys()):
        nodes = layer_nodes[layer]
        parent_groups = group_by_parents(nodes, G)
        
        # Order groups to minimize edge crossings
        if layer == 0:
            sorted_groups = sorted(parent_groups.items(), key=lambda x: sorted(x[1]))
        else:
            def group_key(item):
                parent_set, sibling_nodes = item
                if not parent_set:
                    return (0, sorted(sibling_nodes))
                parent_y_positions = [pos[p][1] for p in parent_set if p in pos]
                avg_y = sum(parent_y_positions) / len(parent_y_positions) if parent_y_positions else 0
                return (avg_y, sorted(sibling_nodes))
            sorted_groups = sorted(parent_groups.items(), key=group_key)
        
        # Position nodes within layer
        group_positions = []
        for parent_set, sibling_nodes in sorted_groups:
            sibling_nodes = sorted(sibling_nodes)
            num_siblings = len(sibling_nodes)
            
            # Determine target y-position
            target_y = None
            if layer > 0 and parent_set:
                parent_y_positions = [pos[p][1] for p in parent_set if p in pos]
                if parent_y_positions:
                    target_y = sum(parent_y_positions) / len(parent_y_positions)
            
            group_positions.append({
                'siblings': sibling_nodes,
                'num_siblings': num_siblings,
                'spacing': sibling_spacing,
                'target_y': target_y
            })
        
        # Assign actual positions, handling overlaps
        node_to_y = {}
        used_y_positions = set()
        
        for group in group_positions:
            sibling_nodes = group['siblings']
            num_siblings = group['num_siblings']
            sibling_spacing = group['spacing']
            target_y = group['target_y']
            group_height = (num_siblings - 1) * sibling_spacing
            
            # Find best y-position
            if target_y is not None:
                start_y = target_y - group_height / 2
                # Check for conflicts (check y positions only)
                test_y_positions = [start_y + i * sibling_spacing for i in range(num_siblings)]
                conflict = any(
                    any(abs(y - used_y) < min_group_spacing for used_y in used_y_positions)
                    for y in test_y_positions
                )
                
                if conflict:
                    # Find nearest non-conflicting position
                    best_start = start_y
                    best_conflict_count = float('inf')
                    search_range, step = 3.0, 0.25
                    for offset in [i * step for i in range(int(-search_range/step), int(search_range/step) + 1)]:
                        test_start = start_y + offset
                        test_positions = [test_start + i * sibling_spacing for i in range(num_siblings)]
                        conflict_count = sum(1 for y in test_positions 
                                            if any(abs(y - used_y) < min_group_spacing for used_y in used_y_positions))
                        if conflict_count < best_conflict_count:
                            best_conflict_count = conflict_count
                            best_start = test_start
                            if best_conflict_count == 0:
                                break
                    start_y = best_start
            else:
                start_y = max(used_y_positions) + min_group_spacing - group_height / 2 if used_y_positions else 0
            
            # Calculate final positions
            sibling_y_positions = ([start_y] if num_siblings == 1 
                                  else [start_y + i * sibling_spacing for i in range(num_siblings)])
            
            # Store positions
            for node, y_pos in zip(sibling_nodes, sibling_y_positions):
                node_to_y[node] = y_pos
                used_y_positions.add(y_pos)
        
        # Center y positions around 0 for this layer
        if node_to_y:
            y_values = list(node_to_y.values())
            if y_values:
                y_center = (max(y_values) + min(y_values)) / 2
                node_to_y = {node: y - y_center for node, y in node_to_y.items()}
        
        # Assign positions
        x = layer * x_spacing
        for node in nodes:
            pos[node] = (x, node_to_y.get(node, 0))
    
    return pos


def get_size_config(num_nodes):
    """Get node size, font size, and figure size based on number of nodes."""
    if num_nodes > 100:
        return 200, 6, (24, 18)
    elif num_nodes > 50:
        return 250, 7, (22, 16)
    elif num_nodes > 25:
        return 300, 8, (20, 14)
    elif num_nodes > 10:
        return 350, 9, (12, 9)
    else:
        # Very small graphs: compact figure size
        return 400, 10, (10, 7.5)


def visualize_descendance_graph(G, output_file='kc_descendance_graph.png', title='Descendance Graph: KC Relationships'):
    """
    Visualize the descendance graph with color-coded nodes.
    - Sources (green): KCs with no antecedents
    - Sinks (red): KCs with no descendants
    - Intermediate (blue): KCs that are neither sources nor sinks
    """
    G = filter_isolated_nodes(G)
    sources, sinks, intermediate = identify_sources_and_sinks(G)
    
    # Get size configuration
    node_size, font_size, figsize = get_size_config(G.number_of_nodes())
    
    # Get layout
    try:
        pos = create_hierarchical_layout_with_clustering(G)
    except Exception as e:
        print(f"Warning: Could not create hierarchical layout: {e}")
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot', args='-Grankdir=LR')
        except:
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Create figure
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    # Optional: Draw background shapes around sibling clusters
    draw_sibling_groups = False
    if draw_sibling_groups:
        try:
            layers = build_layers(G)
            layer_nodes = {}
            for node, layer in layers.items():
                layer_nodes.setdefault(layer, []).append(node)
            
            from matplotlib.patches import Rectangle
            for layer in sorted(layer_nodes.keys()):
                nodes = layer_nodes[layer]
                parent_groups = group_by_parents(nodes, G)
                
                for parent_set, sibling_nodes in parent_groups.items():
                    if len(sibling_nodes) >= 3:
                        sibling_positions = [pos[node] for node in sibling_nodes if node in pos]
                        if len(sibling_positions) >= 2:
                            x_coords = [p[0] for p in sibling_positions]
                            y_coords = [p[1] for p in sibling_positions]
                            padding = 0.2
                            rect = Rectangle((min(x_coords) - padding, min(y_coords) - padding),
                                            max(x_coords) - min(x_coords) + 2*padding,
                                            max(y_coords) - min(y_coords) + 2*padding,
                                            facecolor='lightgray', edgecolor='none',
                                            alpha=0.08, zorder=0)
                            ax.add_patch(rect)
        except:
            pass
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, 
                          edge_color='dimgray', arrows=True, arrowsize=10,
                          arrowstyle='->', connectionstyle='arc3,rad=0.02',
                          alpha=0.7, width=0.8,
                          min_source_margin=5, min_target_margin=5)
    
    # Create labels using Number attribute
    labels = {node: G.nodes[node].get('number', node) for node in G.nodes()}
    
    # Draw nodes by type with color-coding (consolidated)
    node_types = [
        (sources, 'lightgreen', 'darkgreen', 'Source (no antecedents)'),
        (sinks, 'lightcoral', 'darkred', 'Sink (no descendants)'),
        (intermediate, 'lightblue', 'darkblue', 'Intermediate')
    ]
    
    for nodes, fill_color, edge_color, legend_label in node_types:
        if nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=nodes,
                                  node_color=fill_color, node_size=node_size,
                                  node_shape='o', edgecolors=edge_color, linewidths=2)
            label_pos = {node: (pos[node][0] + 0.15, pos[node][1]) for node in nodes}
            nx.draw_networkx_labels(G, label_pos,
                                  labels={node: labels[node] for node in nodes},
                                  font_size=font_size, font_weight='bold',
                                  bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                           edgecolor='none', alpha=0.7))
    
    # Add legend
    legend_elements = [
        Patch(facecolor='lightgreen', edgecolor='darkgreen', label='Source (no antecedents)'),
        Patch(facecolor='lightblue', edgecolor='darkblue', label='Intermediate'),
        Patch(facecolor='lightcoral', edgecolor='darkred', label='Sink (no descendants)')
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=9)
    
    # Title and formatting
    plt.title(title, fontsize=12, fontweight='normal', pad=10, color='gray')
    plt.axis('off')
    
    # Save figure
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Descendance graph saved to {output_file}")
    
    # Display statistics
    print(f"\nGraph Statistics:")
    print(f"  Total KCs: {G.number_of_nodes()}")
    print(f"  Total relationships: {G.number_of_edges()}")
    print(f"  Sources: {len(sources)}")
    print(f"  Sinks: {len(sinks)}")
    print(f"  Intermediate KCs: {len(intermediate)}")
    print(f"  Is acyclic: {nx.is_directed_acyclic_graph(G)}")
    
    if sources:
        print(f"\n  Example sources (first 10): {sources[:10]}")
    if sinks:
        print(f"  Example sinks (first 10): {sinks[:10]}")


def extract_neighborhood(G, kc_nodes, id_to_number):
    """
    Extract the neighborhood subgraph for one or more KCs.
    
    According to the architecture definition: "The neighborhood of a KC x, n(x), 
    in a descendence graph is the descendence graph of the set of KCs that are 
    its immediate antecedents or immediate descendents."
    
    Args:
        G: The full descendance graph
        kc_nodes: List of KC node IDs (or single node ID) to get neighborhood for
        id_to_number: Mapping from KC ID to Number
    
    Returns:
        NetworkX DiGraph: The neighborhood subgraph
    """
    if not isinstance(kc_nodes, list):
        kc_nodes = [kc_nodes]
    
    # Collect all nodes in the neighborhood
    neighborhood_nodes = set()
    
    for kc in kc_nodes:
        if kc not in G:
            print(f"Warning: KC {kc} not found in graph")
            continue
        
        # Add the KC itself
        neighborhood_nodes.add(kc)
        
        # Add all immediate antecedents (direct predecessors)
        # In a descendance graph, predecessors are the nodes that point TO this KC
        # So these are the immediate antecedents of this KC
        antecedents = list(G.predecessors(kc))
        for pred in antecedents:
            neighborhood_nodes.add(pred)
        
        # Add all immediate descendants (direct successors)
        # In a descendance graph, successors are the nodes that this KC points TO
        # So these are the immediate descendants of this KC
        descendants = list(G.successors(kc))
        for succ in descendants:
            neighborhood_nodes.add(succ)
        
        # Debug output
        kc_number = id_to_number.get(kc, kc)
        print(f"\nNeighborhood for KC {kc_number} ({kc}):")
        print(f"  Immediate antecedents: {[id_to_number.get(p, p) for p in antecedents]}")
        print(f"  Immediate descendants: {[id_to_number.get(s, s) for s in descendants]}")
    
    # Create subgraph with all nodes and edges between them
    # This gives us the "descendence graph of the set"
    neighborhood_graph = G.subgraph(neighborhood_nodes).copy()
    
    print(f"\nTotal nodes in neighborhood: {neighborhood_graph.number_of_nodes()}")
    print(f"Total edges in neighborhood: {neighborhood_graph.number_of_edges()}")
    
    return neighborhood_graph


def resolve_kc_identifier(identifier, number_to_id, id_to_number):
    """
    Resolve a KC identifier (could be Number or ID) to the node ID.
    
    Args:
        identifier: KC Number (string) or KC ID
        number_to_id: Mapping from Number to ID
        id_to_number: Mapping from ID to Number
    
    Returns:
        str: The KC node ID, or None if not found
    """
    identifier = identifier.strip()
    
    # Try as Number first
    if identifier in number_to_id:
        return number_to_id[identifier]
    
    # Try as ID
    if identifier in id_to_number:
        return identifier
    
    return None


def visualize_neighborhood(G, kc_identifiers, id_to_number, number_to_id, 
                           output_file='kc_neighborhood.png'):
    """
    Visualize the neighborhood of one or more KCs.
    
    Args:
        G: The full descendance graph
        kc_identifiers: List of KC identifiers (Numbers or IDs) or single identifier
        id_to_number: Mapping from KC ID to Number
        number_to_id: Mapping from KC Number to ID
        output_file: Output filename for the visualization
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
    visualize_descendance_graph(neighborhood_G, 
                               output_file=output_file,
                               title=title)
    
    print(f"\nNeighborhood includes {neighborhood_G.number_of_nodes()} KCs and "
          f"{neighborhood_G.number_of_edges()} relationships.")


def main():
    """Main function to create and visualize the descendance graph from CSV."""
    import sys
    
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'Counting Numbers KCs Nov 2025.csv'
    print(f"Reading KC data from: {csv_file}")
    
    G, id_to_number, _ = create_graph_from_csv(csv_file)
    
    # Get number_to_id mapping for resolving identifiers
    number_to_id = {v: k for k, v in id_to_number.items()}
    
    # Ask user what they want to visualize
    print("\n" + "="*60)
    print("What would you like to visualize?")
    print("1. Full descendance graph")
    print("2. Neighborhood of specific KC(s)")
    print("="*60)
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == '2':
        print("\nEnter KC identifier(s) (Number or ID).")
        print("For multiple KCs, separate with commas (e.g., '1.1, 1.2' or 'KC1, KC2')")
        kc_input = input("KC(s): ").strip()
        
        # Parse input (handle comma-separated list)
        kc_identifiers = [kc.strip() for kc in kc_input.split(',')]
        
        # Generate output filename based on KC numbers
        resolved_ids = []
        for identifier in kc_identifiers:
            node_id = resolve_kc_identifier(identifier, number_to_id, id_to_number)
            if node_id:
                resolved_ids.append(id_to_number.get(node_id, node_id))
        
        if resolved_ids:
            filename = f"kc_neighborhood_{'_'.join(resolved_ids).replace('.', '_')}.png"
        else:
            filename = 'kc_neighborhood.png'
        
        visualize_neighborhood(G, kc_identifiers, id_to_number, number_to_id, 
                              output_file=filename)
    else:
        # Default: visualize full graph
        visualize_descendance_graph(G, 
                                   output_file='kc_descendance_graph.png',
                                   title='Descendance Graph: Counting Numbers KCs')


if __name__ == '__main__':
    main()

