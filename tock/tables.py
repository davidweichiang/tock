import collections
import csv
from . import machines
from . import syntax

try:
    import IPython.display
    from . import viz
except ImportError:
    pass

__all__ = ['from_table', 'read_csv', 'read_excel', 'to_table']

class Table(object):
    """A simple class that just stores a list of lists of strings.
    Compared to `Graph`, this is a lower-level representation."""
    def __init__(self, rows):
        self.rows = rows
    def __getitem__(self, i):
        return self.rows[i]
    def __len__(self):
        return len(self.rows)

    def _repr_html_(self):
        result = []
        result.append('<table style="font-family: Courier, monospace;">')

        for i, row in enumerate(self.rows):
            result.append('  <tr>')
            for j, cell in enumerate(row):
                cell = cell.replace('&', '&epsilon;')
                cell = cell.replace('>', '&gt;')
                if i == 0 or j == 0:
                    result.append('    <th style="text-align: left">{}</th>'.format(cell))
                else:
                    result.append('    <td style="text-align: left">{}</td>'.format(cell))
            result.append('  </tr>')
        
        result.append('</table>')
        return '\n'.join(result)

def from_table(table):
    """Convert a `Table` to a `Machine`."""
    # Ignore blank lines, but keep the line numbers for error reporting
    etable = []
    for i, row in enumerate(table):
        if sum(len(cell.strip()) for cell in row) != 0:
            etable.append((i, row))

    start_state = None
    accept_states = set()
    transitions = []
    
    # Header row has lhs values for all stores other than the first
    lhs2 = []
    i, row = etable[0]
    for j, cell in enumerate(row[1:], 1):
        try:
            lhs2.append(tuple(syntax.string_to_config(cell)))
        except Exception as e:
            e.message = "cell %s%s: %s" % (chr(ord('A')+j), i, e.message)
            raise

    for i, row in etable[1:]:
        # First cell has lhs value for the first store
        try:
            q, attrs = syntax.string_to_state(row[0])
            if attrs.get('start', False):
                if start_state is not None:
                    raise ValueError("more than one start state")
                start_state = q
            if attrs.get('accept', False):
                accept_states.add(q)
            lhs1 = (q,)
        except Exception as e:
            e.message = "cell A%s: %s" % (i+1, e.message)
            raise
        
        # Rest of row has right-hand sides
        if len(row[1:]) != len(lhs2):
            raise ValueError("row %s: row has wrong number of cells" % i)
        for j, cell in enumerate(row[1:], 1):
            try:
                for rhs in syntax.string_to_configs(cell):
                    transitions.append((lhs1+lhs2[j-1], rhs))
            except Exception as e:
                e.message = "cell %s%d: %s" % (chr(ord('A')+j), i+1, e.message)
                raise
        
    if start_state is None:
        raise ValueError("missing start state")
                
    return machines.from_transitions(transitions, start_state, accept_states)

def read_csv(filename):
    """Reads a CSV file containing a tabular description of a transition function,
       as found in Sipser. Major difference: instead of multiple header rows,
       only a single header row whose entries might be tuples.
       """

    with open(filename) as file:
        table = list(csv.reader(file))
    m = from_table(table)
    return m

def read_excel(filename, sheet=None):
    """Reads an Excel file containing a tabular description of a transition function,
       as found in Sipser. Major difference: instead of multiple header rows,
       only a single header row whose entries might be tuples.
       """

    from openpyxl import load_workbook
    wb = load_workbook(filename)
    if sheet is None:
        ws = wb.active
    else:
        ws = wb.get_sheet_by_name(sheet)
    table = [[cell.value or "" for cell in row] for row in ws.rows]
    return from_table(table)

def to_table(m):
    """Converts a `Machine` to a `Table`."""
    rows = []

    states = set()
    initial_state = m.get_start_state()
    final_states = m.get_accept_states()
    conditions = set()
    transitions = collections.defaultdict(list)

    for t in m.get_transitions():
        lhs, rhs = list(t.lhs), list(t.rhs)
        if len(lhs[0]) != 1: 
            raise ValueError("can't convert to table")
        [q] = lhs.pop(m.state)
        condition = tuple(lhs)

        states.add(q)
        conditions.add(condition)
        transitions[q,condition].append(rhs)
    states.update(final_states)

    conditions = sorted(conditions)
    row = ['']
    for condition in conditions:
        row.append(','.join(map(str, condition)))
    rows.append(row)

    for q in sorted(states):
        row = []
        qstring = q
        if q == initial_state:
            qstring = ">" + qstring
        if q in final_states:
            qstring = "@" + qstring
        row.append(qstring)
        for condition in conditions:
            row.append(configs_to_string(transitions[q,condition]))
        rows.append(row)
    return Table(rows)

def configs_to_string(configs):
    if len(configs) == 0:
        return ""
    if len(configs) == 1:
        [config] = configs
        return ','.join(map(str, config))
    strings = []
    for config in sorted(configs):
        if len(config) == 1:
            [store] = config
            strings.append(str(store))
        else:
            strings.append('(%s)' % ','.join(map(str, config)))
    return '{%s}' % ','.join(strings)

