import collections
from . import machines
from . import syntax

__all__ = ['run_pda']

def run_pda(m, w, trace=False, show_stack=0):
    """Runs a nondeterministic pushdown automaton using the cubic
    algorithm of: Bernard Lang, "Deterministic techniques for efficient 
    non-deterministic parsers." doi:10.1007/3-540-06841-4_65 .

    `m`: the pushdown automaton
    `w`: the input string

    Store 1 is assumed to be the input, and store 2 is assumed to be the stack.
    Currently we don't allow any other stores, though additional cells would
    be fine.
    """

    """The items are pairs of configurations (parent, child), where

       - parent is None and child's stack has no elided items
       - child has one more elided item than parent
    """

    """
    Axiom:
    
    ------------------
    [None => q0, 0, &]
    
    Push:
    
    [q, i, yz => r, j, xy']
    -----------------------
    [r, j, xy' => r, j, x]
    
    Pop:
    
    [q, i, yz => r, j, xy'] [r, j, xy' => s, k, &]
    ----------------------------------------------
                 [q, i, yz => s, k, y']
    """

    from .machines import Store, Run

    agenda = collections.deque()
    goals = []
    chart = set()
    index_left = collections.defaultdict(set)
    index_right = collections.defaultdict(set)
    backpointers = collections.defaultdict(set)
    visible = set()
    run = Run(m)

    # which position the state, input and stack are in
    qi, ii, si = 0, 1, 2
    if not m.has_stack(si):
        raise ValueError("store %s must be a stack" % si)

    # how much of the stack is not elided
    show_stack = max(show_stack, 
                     max(len(t.lhs[si]) for t in m.transitions), 
                     max(len(c[si]) for c in m.accept_configs))

    # Axiom
    input_tokens = syntax.lexer(w)
    config = list(m.start_config)
    config[m.input] = Store(input_tokens)
    config = tuple(config)

    def simplify(parent, child):
        """Map a parent=>child item into a node in the run graph.
           If parent is not None, just append a ..."""
        if parent is None:
            return child
        else:
            child = list(child)
            child[si] = Store(child[si].values + ["..."], child[si].position)
            return tuple(child)

    agenda.append((None, config))
    run.set_start_config(simplify(None, config))

    # Final configurations
    # Since there is no Configuration class, we need to make a fake Transition
    final_transitions = []
    for config in m.accept_configs:
        final_transitions.append(machines.Transition(config, [[]]*m.num_stores))

    def add(parent, child):
        if (parent, child) in chart:
            if trace: print("merge: {} => {}".format(parent, child))
        else:
            chart.add((parent, child))
            if trace: print("add: {} => {}".format(parent, child))
            agenda.append((parent, child))

    while len(agenda) > 0:
        parent, child = agenda.popleft()
        if trace: print("trigger: {} => {}".format(parent, child))

        for t in final_transitions:
            if t.match(child):
                run.add_accept_config(simplify(parent, child))

        # The stack shows too many items (push)
        if len(child[si]) > show_stack:
            grandchild = tuple(s.copy() for s in child)
            del grandchild[si].values[-1]
            add(child, grandchild)
            index_right[child].add(parent)
            for ant in backpointers[simplify(parent, child)]:
                backpointers[simplify(child, grandchild)].add(ant)

            # This item can also be the left antecedent of the Pop rule
            for grandchild in index_left[child]:
                grandchild = tuple(s.copy() for s in grandchild)
                grandchild[si].values.append(child[si][-1])
                add(parent, grandchild)
                for ant in backpointers[simplify(parent, child)]:
                    backpointers[simplify(parent, grandchild)].add(ant)

        # The stack shows too few items (pop)
        elif parent is not None and len(child[si]) < show_stack:
            aunt = tuple(s.copy() for s in child)
            if len(parent[si]) == 0:
                assert False
            else:
                aunt[si].values.append(parent[si][-1])
            index_left[parent].add(child)

            for grandparent in index_right[parent]:
                add(grandparent, aunt)

            for ant in backpointers[simplify(parent, child)]:
                backpointers[simplify(grandparent, aunt)].add(ant)

        # The stack is just right
        else:
            run.configs.add(simplify(parent, child))
            for transition in m.transitions:
                if transition.match(child):
                    sister = transition.apply(child)
                    add(parent, sister)
                    backpointers[simplify(parent, sister)].add(simplify(parent, child))

    # Add run edges only between configurations whose stack is
    # just right
    for config2 in run.configs:
        for config1 in backpointers[config2]:
            run.add_edge(config1, config2)

    return run

if __name__ == "__main__":
    import formats
    m = formats.read_csv("../examples/pda.csv")
    run_pda(m, "0 0 0 1 1 1", trace=True)