# Storage structure of instrument information

Information about experimental instruments is stored in a vector database.

- There is a root node in the database, and all instrument nodes are the children of this root node.
- Each instrument node contains the following information:

  - Instrument name
  - Instrument description
  - Super Users (responsible for managing instrument information, laboratory members with full access to the instruments)
- For each instrument, the instrument information is recorded as child nodes of the instrument node, 
such as usage specifications, operating manuals, instrument parameters, etc.

Refer to **Code docs** `Func_modules.instrument.store.instrument_store` for more details.