#from sqlalchemy.sql.expression import ClauseElement
from sqlalchemy.schema import DDLElement 
from sqlalchemy.ext.compiler import compiles

class TriggerProcedure(DDLElement):

    def __init__(self, name, script, trigger_type='trigger'):
        if trigger_type not in ['event_trigger', 'trigger']:
            raise Exception('Unknown trigger type: %s.' % trigger_type)
        self.name = name 
        self.script = script
        self.trigger_type = trigger_type

@compiles(TriggerProcedure, 'postgresql')
def render_trigger_procedure(element, compiler):
    template = """
    CREATE OR REPLACE FUNCTION {name}() RETURNS {trigger_type} AS 
    $script$
    BEGIN
    {script}
    END;
    $script$ language plpgsql;
    """
    rv = template.format(name=element.name,
                         script=element.script, 
                         trigger_type=element.trigger_type)
    return rv

def needle_set(needles):
    try:
        needles = {needles.upper()}
    except AttributeError:
        needles = {n.upper() for n in needles}
    return needles

class Trigger(DDLElement):
    allowed_when = {'BEFORE', 'AFTER', 'INSTEAD OF'}
    allowed_events = {'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'}
    allowed_levels = {'ROW', 'STATEMENT'}

    def __init__(self, trigger_name, table, procedure, events, level='ROW',
                 when='BEFORE'):

        if when.upper() not in self.allowed_when:
            raise Exception('Unknown WHEN condition: %s.' % when)

        if level not in self.allowed_levels:
            raise Exception('Unknown trigger level: FOR EACH %s.' % level)
        events = needle_set(events)
        diff = events.difference(self.allowed_events)
        if diff:
            raise Exception('Unknown event conditions: %s.' % ', '.join(diff))

        self.trigger_name = trigger_name
        try:
            self.table_name = table.__table__.name
        except AttributeError:
            try:
                self.table_name = table.name
            except AttributeError:
                self.table_name = table
        try:
            self.procedure = procedure.name
        except AttributeError:
            self.procedure = procedure
        self.events = events
        self.level = level
        self.when = when

@compiles(Trigger, 'postgresql')
def render_trigger(element, compiler, **kw):
    template = """
    DROP TRIGGER IF EXISTS {trigger_name} on {table_name} CASCADE;
    CREATE TRIGGER {trigger_name} {when} {events}
    ON {table_name}
    FOR EACH {level}
    EXECUTE PROCEDURE {trigger_procedure}();
    """
    rv = template.format(
        trigger_name=element.trigger_name,
        table_name=element.table_name,
        when=element.when,
        events=' OR '.join(element.events),
        level=element.level,
        trigger_procedure=element.procedure,
    )
    return rv
