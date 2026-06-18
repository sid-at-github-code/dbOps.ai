"""
Database schema context fed to the LLM as its system message.

Fill in full_db_context_helper with a description of every table,
column, type, and relationship in your PostgreSQL database.
The more precise this is, the better the generated SQL will be.

Example structure:
    You are a PostgreSQL expert. Given the schema below, write a single
    read-only SELECT query that answers the user's question. Return only
    the SQL — no explanation, no markdown fences.

"""

full_db_context_helper: str = """
You are a PostgreSQL expert. Given the schema below, write a single
read-only SELECT query that answers the user's question exactly.

# AdventureWorks PostgreSQL — Master NL-to-SQL Context File

> Feed this entire file as the **system prompt context** to your LLM for NL-to-SQL generation.
> This covers all 68 tables across 5 schemas, all foreign key relationships, all views,
> column-level semantics, common join paths, and query patterns for complex queries.

---

## 1. DATABASE OVERVIEW

**Database:** AdventureWorks (PostgreSQL port of Microsoft's AdventureWorks 2014 OLTP sample)
**Dialect:** PostgreSQL (Supabase-hosted)
**Schemas:** `person`, `humanresources`, `production`, `purchasing`, `sales`
**Total Tables:** 68
**Total Views:** 20 semantic views + 68 convenience shorthand views (schemas: `pe`, `hr`, `pr`, `pu`, `sa`)

### Schema Responsibilities

| Schema | Purpose |
|--------|---------|
| `person` | People, addresses, contact info — shared by employees, customers, vendors |
| `humanresources` | Employees, departments, shifts, pay history, job candidates |
| `production` | Products, inventory, manufacturing, work orders, BOM |
| `purchasing` | Vendors, purchase orders, ship methods |
| `sales` | Customers, sales orders, territories, sales reps, promotions |

---

## 2. NAMING & IDENTIFIER CONVENTIONS

- **Primary keys** are typically `<EntityName>ID` (e.g., `ProductID`, `CustomerID`)
- **BusinessEntityID** is the universal identity key shared across `Person.BusinessEntity`, `Person.Person`, `HumanResources.Employee`, `Sales.SalesPerson`, `Purchasing.Vendor`, `Sales.Store`
- **All schema names are case-sensitive** in quotes but lowercase is safe with PostgreSQL: use `person.person`, `humanresources.employee`, etc.
- **Timestamps** use PostgreSQL `TIMESTAMP` type (not `DATETIME`)
- **Money** fields use `numeric` type (not `money` type)
- **Flags/Booleans** use custom domain `"Flag"` = `boolean NOT NULL`
- **Names** use custom domain `"Name"` = `varchar(50)`
- `rowguid` columns are UUID auto-generated — not useful for queries, ignore unless joining on document identity

---

## 3. FULL SCHEMA — TABLE × COLUMN REFERENCE

### 3.1 Schema: `person`

#### `person.businessentity`
The root identity record. Every person, vendor, store, and employee starts here.
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | SERIAL PK | Universal ID across the system |
| `rowguid` | uuid | Auto-generated, rarely needed |
| `modifieddate` | TIMESTAMP | Last update time |

#### `person.person`
All humans in the system — employees, customers, vendor contacts.
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.businessentity` |
| `persontype` | char(2) | `SC`=Store Contact, `IN`=Individual Customer, `SP`=Sales Person, `EM`=Employee, `VC`=Vendor Contact, `GC`=General Contact |
| `namestyle` | boolean | `false`=Western order (First Last), `true`=Eastern order (Last First) |
| `title` | varchar(8) | Mr., Ms., Dr., etc. |
| `firstname` | varchar(50) | |
| `middlename` | varchar(50) | Nullable |
| `lastname` | varchar(50) | |
| `suffix` | varchar(10) | Jr., Sr., etc. Nullable |
| `emailpromotion` | INT | `0`=No email, `1`=AW emails, `2`=AW + partner emails |
| `additionalcontactinfo` | XML | Extra contact data in XML |
| `demographics` | XML | Survey data (income, hobbies, purchases) |
| `modifieddate` | TIMESTAMP | |

#### `person.address`
Physical addresses shared by employees, customers, vendors.
| Column | Type | Notes |
|--------|------|-------|
| `addressid` | SERIAL PK | |
| `addressline1` | varchar(60) | Street line 1 |
| `addressline2` | varchar(60) | Nullable |
| `city` | varchar(30) | |
| `stateprovinceid` | INT FK | → `person.stateprovince` |
| `postalcode` | varchar(15) | |
| `spatiallocation` | varchar(44) | Lat/long string |
| `modifieddate` | TIMESTAMP | |

#### `person.stateprovince`
| Column | Type | Notes |
|--------|------|-------|
| `stateprovinceid` | SERIAL PK | |
| `stateprovincecode` | char(3) | ISO state/province code |
| `countryregioncode` | varchar(3) FK | → `person.countryregion` |
| `isonlystateprovinceflag` | boolean | `true` if country has no states (uses country code only) |
| `name` | varchar(50) | State/province name |
| `territoryid` | INT FK | → `sales.salesterritory` |
| `modifieddate` | TIMESTAMP | |

#### `person.countryregion`
| Column | Type | Notes |
|--------|------|-------|
| `countryregioncode` | varchar(3) PK | ISO 3-letter country code |
| `name` | varchar(50) | Country name |
| `modifieddate` | TIMESTAMP | |

#### `person.addresstype`
| Column | Type | Notes |
|--------|------|-------|
| `addresstypeid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `Billing`, `Home`, `Shipping`, `Main Office` |
| `modifieddate` | TIMESTAMP | |

#### `person.businessentityaddress`
Links entities (people/vendors/stores) to addresses with type.
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.businessentity` |
| `addressid` | INT PK/FK | → `person.address` |
| `addresstypeid` | INT PK/FK | → `person.addresstype` |
| `modifieddate` | TIMESTAMP | |

#### `person.contacttype`
| Column | Type | Notes |
|--------|------|-------|
| `contacttypeid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `Owner`, `Purchasing Manager`, `Sales Agent` |
| `modifieddate` | TIMESTAMP | |

#### `person.businessentitycontact`
Links stores/vendors to their contact persons.
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | The store or vendor |
| `personid` | INT PK/FK | → `person.person` |
| `contacttypeid` | INT PK/FK | → `person.contacttype` |
| `modifieddate` | TIMESTAMP | |

#### `person.emailaddress`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.person` |
| `emailaddressid` | SERIAL PK | |
| `emailaddress` | varchar(50) | Actual email string |
| `modifieddate` | TIMESTAMP | |

#### `person.password`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.person` |
| `passwordhash` | varchar(128) | One-way hash |
| `passwordsalt` | varchar(10) | Random salt |
| `modifieddate` | TIMESTAMP | |

#### `person.phonenumbertype`
| Column | Type | Notes |
|--------|------|-------|
| `phonenumbertypeid` | SERIAL PK | |
| `name` | varchar(50) | `Cell`, `Home`, `Work` |
| `modifieddate` | TIMESTAMP | |

#### `person.personphone`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.person` |
| `phonenumber` | varchar(25) PK | |
| `phonenumbertypeid` | INT PK/FK | → `person.phonenumbertype` |
| `modifieddate` | TIMESTAMP | |

---

### 3.2 Schema: `humanresources`

#### `humanresources.employee`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.person` |
| `nationalidnumber` | varchar(15) | SSN or equivalent |
| `loginid` | varchar(256) | Network login |
| `organizationnode` | varchar | Hierarchy path e.g. `/1/`, `/1/2/` |
| `jobtitle` | varchar(50) | Job role |
| `birthdate` | DATE | |
| `maritalstatus` | char(1) | `M`=Married, `S`=Single |
| `gender` | char(1) | `M`=Male, `F`=Female |
| `hiredate` | DATE | |
| `salariedflag` | boolean | `true`=Salaried, `false`=Hourly |
| `vacationhours` | smallint | Available vacation hours |
| `sickleavehours` | smallint | Available sick leave hours |
| `currentflag` | boolean | `true`=Active employee |
| `modifieddate` | TIMESTAMP | |

#### `humanresources.department`
| Column | Type | Notes |
|--------|------|-------|
| `departmentid` | SERIAL PK | |
| `name` | varchar(50) | Department name |
| `groupname` | varchar(50) | Parent group (e.g., `Manufacturing`, `Sales and Marketing`) |
| `modifieddate` | TIMESTAMP | |

#### `humanresources.employeedepartmenthistory`
Tracks which department an employee was in and when.
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `humanresources.employee` |
| `departmentid` | INT PK/FK | → `humanresources.department` |
| `shiftid` | INT PK/FK | → `humanresources.shift` |
| `startdate` | DATE PK | When assignment started |
| `enddate` | DATE | NULL = currently in this department |
| `modifieddate` | TIMESTAMP | |

**Key pattern:** `WHERE enddate IS NULL` → current department

#### `humanresources.employeepayhistory`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `humanresources.employee` |
| `ratechangedate` | TIMESTAMP PK | When rate changed |
| `rate` | numeric | Hourly rate (6.50–200.00) |
| `payfrequency` | smallint | `1`=Monthly, `2`=Biweekly |
| `modifieddate` | TIMESTAMP | |

**Key pattern:** To get current rate: `ORDER BY ratechangedate DESC LIMIT 1` per employee

#### `humanresources.shift`
| Column | Type | Notes |
|--------|------|-------|
| `shiftid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `Day`, `Evening`, `Night` |
| `starttime` | time | |
| `endtime` | time | |
| `modifieddate` | TIMESTAMP | |

#### `humanresources.jobcandidate`
| Column | Type | Notes |
|--------|------|-------|
| `jobcandidateid` | SERIAL PK | |
| `businessentityid` | INT FK | → `humanresources.employee` (if hired, else NULL) |
| `resume` | XML | Full resume in XML format |
| `modifieddate` | TIMESTAMP | |

---

### 3.3 Schema: `production`

#### `production.product`
Central product table. Core of the production schema.
| Column | Type | Notes |
|--------|------|-------|
| `productid` | SERIAL PK | |
| `name` | varchar(50) | Product name |
| `productnumber` | varchar(25) | Internal product code (e.g., `BK-R93R-62`) |
| `makeflag` | boolean | `true`=Made in-house, `false`=Purchased |
| `finishedgoodsflag` | boolean | `true`=Saleable finished product |
| `color` | varchar(15) | Nullable |
| `safetystocklevel` | smallint | Minimum inventory quantity |
| `reorderpoint` | smallint | Trigger level for reorder |
| `standardcost` | numeric | Internal cost |
| `listprice` | numeric | Selling price (0 = not for direct sale) |
| `size` | varchar(5) | S, M, L, XL, etc. Nullable |
| `sizeunitmeasurecode` | char(3) FK | → `production.unitmeasure` |
| `weightunitmeasurecode` | char(3) FK | → `production.unitmeasure` |
| `weight` | decimal(8,2) | Nullable |
| `daystomanufacture` | INT | Lead time |
| `productline` | char(2) | `R`=Road, `M`=Mountain, `T`=Touring, `S`=Standard. Nullable |
| `class` | char(2) | `H`=High, `M`=Medium, `L`=Low. Nullable |
| `style` | char(2) | `W`=Womens, `M`=Mens, `U`=Universal. Nullable |
| `productsubcategoryid` | INT FK | → `production.productsubcategory`. Nullable |
| `productmodelid` | INT FK | → `production.productmodel`. Nullable |
| `sellstartdate` | TIMESTAMP | When product went on sale |
| `sellenddate` | TIMESTAMP | Nullable — NULL = still for sale |
| `discontinueddate` | TIMESTAMP | Nullable |
| `modifieddate` | TIMESTAMP | |

#### `production.productcategory`
Top-level product grouping.
| Column | Type | Notes |
|--------|------|-------|
| `productcategoryid` | SERIAL PK | |
| `name` | varchar(50) | `Bikes`, `Components`, `Clothing`, `Accessories` |
| `modifieddate` | TIMESTAMP | |

#### `production.productsubcategory`
| Column | Type | Notes |
|--------|------|-------|
| `productsubcategoryid` | SERIAL PK | |
| `productcategoryid` | INT FK | → `production.productcategory` |
| `name` | varchar(50) | E.g., `Mountain Bikes`, `Road Bikes`, `Helmets` |
| `modifieddate` | TIMESTAMP | |

#### `production.productmodel`
| Column | Type | Notes |
|--------|------|-------|
| `productmodelid` | SERIAL PK | |
| `name` | varchar(50) | Model name |
| `catalogdescription` | XML | Rich product catalog XML |
| `instructions` | XML | Manufacturing instructions XML |
| `modifieddate` | TIMESTAMP | |

#### `production.productdescription`
| Column | Type | Notes |
|--------|------|-------|
| `productdescriptionid` | SERIAL PK | |
| `description` | varchar(400) | Product description text |
| `modifieddate` | TIMESTAMP | |

#### `production.productmodelproductdescriptionculture`
Links model → description → language (culture).
| Column | Type | Notes |
|--------|------|-------|
| `productmodelid` | INT PK/FK | → `production.productmodel` |
| `productdescriptionid` | INT PK/FK | → `production.productdescription` |
| `cultureid` | char(6) PK/FK | → `production.culture` |
| `modifieddate` | TIMESTAMP | |

#### `production.culture`
| Column | Type | Notes |
|--------|------|-------|
| `cultureid` | char(6) PK | ISO culture code (e.g., `en`, `fr`, `ar`) |
| `name` | varchar(50) | Language name |
| `modifieddate` | TIMESTAMP | |

#### `production.unitmeasure`
| Column | Type | Notes |
|--------|------|-------|
| `unitmeasurecode` | char(3) PK | E.g., `LB`, `KG`, `EA`, `IN` |
| `name` | varchar(50) | Full name |
| `modifieddate` | TIMESTAMP | |

#### `production.productinventory`
Current inventory levels per product per location.
| Column | Type | Notes |
|--------|------|-------|
| `productid` | INT PK/FK | → `production.product` |
| `locationid` | INT PK/FK | → `production.location` |
| `shelf` | varchar(10) | Storage shelf label |
| `bin` | smallint | Bin number (0–100) |
| `quantity` | smallint | Current stock count |
| `modifieddate` | TIMESTAMP | |

#### `production.location`
Manufacturing/warehouse locations.
| Column | Type | Notes |
|--------|------|-------|
| `locationid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `Tool Crib`, `Frame Forming` |
| `costrate` | numeric | Hourly cost rate |
| `availability` | decimal(8,2) | Work capacity in hours |
| `modifieddate` | TIMESTAMP | |

#### `production.productcosthistory`
| Column | Type | Notes |
|--------|------|-------|
| `productid` | INT PK/FK | → `production.product` |
| `startdate` | TIMESTAMP PK | |
| `enddate` | TIMESTAMP | NULL = current cost |
| `standardcost` | numeric | |
| `modifieddate` | TIMESTAMP | |

#### `production.productlistpricehistory`
| Column | Type | Notes |
|--------|------|-------|
| `productid` | INT PK/FK | → `production.product` |
| `startdate` | TIMESTAMP PK | |
| `enddate` | TIMESTAMP | NULL = current price |
| `listprice` | numeric | |
| `modifieddate` | TIMESTAMP | |

#### `production.productphoto`
| Column | Type | Notes |
|--------|------|-------|
| `productphotoid` | SERIAL PK | |
| `thumbnailphoto` | bytea | Binary thumbnail |
| `thumbnailphotofilename` | varchar(50) | |
| `largephoto` | bytea | Binary full image |
| `largephotofilename` | varchar(50) | |
| `modifieddate` | TIMESTAMP | |

#### `production.productproductphoto`
| Column | Type | Notes |
|--------|------|-------|
| `productid` | INT PK/FK | → `production.product` |
| `productphotoid` | INT PK/FK | → `production.productphoto` |
| `primary` | boolean | `true` = main product image |
| `modifieddate` | TIMESTAMP | |

#### `production.productreview`
Customer product reviews.
| Column | Type | Notes |
|--------|------|-------|
| `productreviewid` | SERIAL PK | |
| `productid` | INT FK | → `production.product` |
| `reviewername` | varchar(50) | |
| `reviewdate` | TIMESTAMP | |
| `emailaddress` | varchar(50) | Reviewer email |
| `rating` | INT | 1–5 scale |
| `comments` | varchar(3850) | Review text |
| `modifieddate` | TIMESTAMP | |

#### `production.billofmaterials`
Component hierarchy for product assembly.
| Column | Type | Notes |
|--------|------|-------|
| `billofmaterialsid` | SERIAL PK | |
| `productassemblyid` | INT FK | Parent product → `production.product`. NULL = top-level |
| `componentid` | INT FK | Child component → `production.product` |
| `startdate` | TIMESTAMP | When component started being used |
| `enddate` | TIMESTAMP | NULL = currently used |
| `unitmeasurecode` | char(3) FK | → `production.unitmeasure` |
| `bomlevel` | smallint | Depth in hierarchy (0 = top) |
| `perassemblyqty` | decimal(8,2) | How many components per assembly |
| `modifieddate` | TIMESTAMP | |

#### `production.scrapreason`
| Column | Type | Notes |
|--------|------|-------|
| `scrapreasonid` | SERIAL PK | |
| `name` | varchar(50) | Reason (e.g., `Trim Cutting`, `Drill Size Too Small`) |
| `modifieddate` | TIMESTAMP | |

#### `production.workorder`
Manufacturing work orders.
| Column | Type | Notes |
|--------|------|-------|
| `workorderid` | SERIAL PK | |
| `productid` | INT FK | → `production.product` |
| `orderqty` | INT | Quantity to build |
| `scrappedqty` | smallint | Failed inspection count |
| `startdate` | TIMESTAMP | |
| `enddate` | TIMESTAMP | Nullable |
| `duedate` | TIMESTAMP | |
| `scrapreasonid` | INT FK | → `production.scrapreason`. Nullable |
| `modifieddate` | TIMESTAMP | |

#### `production.workorderrouting`
Operations/steps within a work order.
| Column | Type | Notes |
|--------|------|-------|
| `workorderid` | INT PK/FK | → `production.workorder` |
| `productid` | INT PK/FK | → `production.product` |
| `operationsequence` | smallint PK | Step number |
| `locationid` | INT FK | → `production.location` |
| `scheduledstartdate` | TIMESTAMP | |
| `scheduledenddate` | TIMESTAMP | |
| `actualstartdate` | TIMESTAMP | Nullable |
| `actualenddate` | TIMESTAMP | Nullable |
| `actualresourcehrs` | decimal(9,4) | Actual hours used |
| `plannedcost` | numeric | Estimated cost |
| `actualcost` | numeric | Nullable |
| `modifieddate` | TIMESTAMP | |

#### `production.transactionhistory`
Every inventory transaction (sales, purchases, work orders) for current year.
| Column | Type | Notes |
|--------|------|-------|
| `transactionid` | SERIAL PK | |
| `productid` | INT FK | → `production.product` |
| `referenceorderid` | INT | The source order ID |
| `referenceorderlineid` | INT | Line item within source order |
| `transactiondate` | TIMESTAMP | |
| `transactiontype` | char(1) | `W`=WorkOrder, `S`=SalesOrder, `P`=PurchaseOrder |
| `quantity` | INT | |
| `actualcost` | numeric | |
| `modifieddate` | TIMESTAMP | |

#### `production.transactionhistoryarchive`
Same structure as `transactionhistory` but for prior years.

#### `production.document`
Product maintenance documents.
| Column | Type | Notes |
|--------|------|-------|
| `documentnode` | varchar PK | Hierarchy path |
| `title` | varchar(50) | Document title |
| `owner` | INT FK | → `humanresources.employee` |
| `folderflag` | boolean | `false`=document, `true`=folder |
| `filename` | varchar(400) | |
| `fileextension` | varchar(8) | `.doc`, `.txt`, etc. |
| `revision` | char(5) | Version |
| `changenumber` | INT | Engineering change number |
| `status` | smallint | `1`=Pending, `2`=Approved, `3`=Obsolete |
| `documentsummary` | text | Abstract |
| `document` | bytea | Full binary document |
| `modifieddate` | TIMESTAMP | |

#### `production.productdocument`
| Column | Type | Notes |
|--------|------|-------|
| `productid` | INT PK/FK | → `production.product` |
| `documentnode` | varchar PK/FK | → `production.document` |
| `modifieddate` | TIMESTAMP | |

#### `production.illustration`
| Column | Type | Notes |
|--------|------|-------|
| `illustrationid` | SERIAL PK | |
| `diagram` | XML | Assembly diagram in XML |
| `modifieddate` | TIMESTAMP | |

#### `production.productmodelillustration`
| Column | Type | Notes |
|--------|------|-------|
| `productmodelid` | INT PK/FK | → `production.productmodel` |
| `illustrationid` | INT PK/FK | → `production.illustration` |
| `modifieddate` | TIMESTAMP | |

---

### 3.4 Schema: `purchasing`

#### `purchasing.vendor`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.businessentity` |
| `accountnumber` | varchar(15) | Vendor account number |
| `name` | varchar(50) | Company name |
| `creditrating` | smallint | `1`=Superior … `5`=Below average |
| `preferredvendorstatus` | boolean | `true`=Preferred vendor |
| `activeflag` | boolean | `true`=Currently active |
| `purchasingwebserviceurl` | varchar(1024) | Vendor's web service URL |
| `modifieddate` | TIMESTAMP | |

#### `purchasing.productvendor`
Maps products to the vendors that supply them.
| Column | Type | Notes |
|--------|------|-------|
| `productid` | INT PK/FK | → `production.product` |
| `businessentityid` | INT PK/FK | → `purchasing.vendor` |
| `averageleadtime` | INT | Days between order and receipt |
| `standardprice` | numeric | Vendor's usual price |
| `lastreceiptcost` | numeric | Price at last receipt. Nullable |
| `lastreceiptdate` | TIMESTAMP | Nullable |
| `minorderqty` | INT | Minimum order quantity |
| `maxorderqty` | INT | Maximum order quantity |
| `onorderqty` | INT | Currently on order. Nullable |
| `unitmeasurecode` | char(3) FK | → `production.unitmeasure` |
| `modifieddate` | TIMESTAMP | |

#### `purchasing.purchaseorderheader`
| Column | Type | Notes |
|--------|------|-------|
| `purchaseorderid` | SERIAL PK | |
| `revisionnumber` | smallint | Version tracker |
| `status` | smallint | `1`=Pending, `2`=Approved, `3`=Rejected, `4`=Complete |
| `employeeid` | INT FK | → `humanresources.employee` (who created it) |
| `vendorid` | INT FK | → `purchasing.vendor` |
| `shipmethodid` | INT FK | → `purchasing.shipmethod` |
| `orderdate` | TIMESTAMP | |
| `shipdate` | TIMESTAMP | Nullable |
| `subtotal` | numeric | |
| `taxamt` | numeric | |
| `freight` | numeric | |
| `totaldue` | numeric | `subtotal + taxamt + freight` |
| `modifieddate` | TIMESTAMP | |

#### `purchasing.purchaseorderdetail`
Line items within a purchase order.
| Column | Type | Notes |
|--------|------|-------|
| `purchaseorderid` | INT PK/FK | → `purchasing.purchaseorderheader` |
| `purchaseorderdetailid` | SERIAL PK | |
| `duedate` | TIMESTAMP | Expected receipt date |
| `orderqty` | smallint | Quantity ordered |
| `productid` | INT FK | → `production.product` |
| `unitprice` | numeric | Vendor price per unit |
| `receivedqty` | decimal(8,2) | Actual received |
| `rejectedqty` | decimal(8,2) | Failed inspection |
| `modifieddate` | TIMESTAMP | |

**Note:** `linetotal = orderqty * unitprice` and `stockedqty = receivedqty - rejectedqty` are computed, not stored.

#### `purchasing.shipmethod`
| Column | Type | Notes |
|--------|------|-------|
| `shipmethodid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `CARGO TRANSPORT 5`, `OVERNIGHT J-FAST` |
| `shipbase` | numeric | Base shipping charge |
| `shiprate` | numeric | Per-pound rate |
| `modifieddate` | TIMESTAMP | |

---

### 3.5 Schema: `sales`

#### `sales.customer`
| Column | Type | Notes |
|--------|------|-------|
| `customerid` | SERIAL PK | |
| `personid` | INT FK | → `person.person`. NULL if store-only |
| `storeid` | INT FK | → `sales.store`. NULL if individual customer |
| `territoryid` | INT FK | → `sales.salesterritory`. Nullable |
| `modifieddate` | TIMESTAMP | |

**Key pattern:** Individual customers have `personid` set; B2B customers have `storeid` set.

#### `sales.store`
Reseller/retailer customers.
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.businessentity` |
| `name` | varchar(50) | Store name |
| `salespersonid` | INT FK | → `sales.salesperson`. Assigned rep |
| `demographics` | XML | Store survey data |
| `modifieddate` | TIMESTAMP | |

#### `sales.salesperson`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `humanresources.employee` |
| `territoryid` | INT FK | → `sales.salesterritory`. Nullable |
| `salesquota` | numeric | Annual quota. Nullable |
| `bonus` | numeric | Bonus if quota met |
| `commissionpct` | numeric | Commission rate |
| `salesytd` | numeric | Year-to-date sales |
| `saleslastyear` | numeric | Prior year total |
| `modifieddate` | TIMESTAMP | |

#### `sales.salesterritory`
| Column | Type | Notes |
|--------|------|-------|
| `territoryid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `Northwest`, `Southwest`, `Canada` |
| `countryregioncode` | varchar(3) FK | → `person.countryregion` |
| `group` | varchar(50) | Geographic group: `North America`, `Europe`, `Pacific` |
| `salesytd` | numeric | Territory YTD sales |
| `saleslastyear` | numeric | Prior year |
| `costytd` | numeric | Territory costs YTD |
| `costlastyear` | numeric | |
| `modifieddate` | TIMESTAMP | |

#### `sales.salesterritoryhistory`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `sales.salesperson` |
| `territoryid` | INT PK/FK | → `sales.salesterritory` |
| `startdate` | TIMESTAMP PK | |
| `enddate` | TIMESTAMP | NULL = current assignment |
| `modifieddate` | TIMESTAMP | |

#### `sales.salespersonquotahistory`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `sales.salesperson` |
| `quotadate` | TIMESTAMP PK | |
| `salesquota` | numeric | |
| `modifieddate` | TIMESTAMP | |

#### `sales.salesorderheader`
Main sales order table — one row per order.
| Column | Type | Notes |
|--------|------|-------|
| `salesorderid` | SERIAL PK | |
| `revisionnumber` | smallint | Version tracker |
| `orderdate` | TIMESTAMP | When order was placed |
| `duedate` | TIMESTAMP | When order is due |
| `shipdate` | TIMESTAMP | Nullable — NULL if not yet shipped |
| `status` | smallint | `1`=In process, `2`=Approved, `3`=Backordered, `4`=Rejected, `5`=Shipped, `6`=Cancelled |
| `onlineorderflag` | boolean | `true`=Online order, `false`=Sales rep order |
| `purchaseordernumber` | varchar(25) | Customer's PO reference. Nullable |
| `accountnumber` | varchar(15) | Accounting reference. Nullable |
| `customerid` | INT FK | → `sales.customer` |
| `salespersonid` | INT FK | → `sales.salesperson`. Nullable (NULL if online) |
| `territoryid` | INT FK | → `sales.salesterritory`. Nullable |
| `billtoaddressid` | INT FK | → `person.address` |
| `shiptoaddressid` | INT FK | → `person.address` |
| `shipmethodid` | INT FK | → `purchasing.shipmethod` |
| `creditcardid` | INT FK | → `sales.creditcard`. Nullable |
| `creditcardapprovalcode` | varchar(15) | Nullable |
| `currencyrateid` | INT FK | → `sales.currencyrate`. Nullable |
| `subtotal` | numeric | Sum of line totals |
| `taxamt` | numeric | |
| `freight` | numeric | |
| `totaldue` | numeric | `subtotal + taxamt + freight` |
| `comment` | varchar(128) | Rep notes. Nullable |
| `modifieddate` | TIMESTAMP | |

#### `sales.salesorderdetail`
Line items within a sales order.
| Column | Type | Notes |
|--------|------|-------|
| `salesorderid` | INT PK/FK | → `sales.salesorderheader` (CASCADE DELETE) |
| `salesorderdetailid` | SERIAL PK | |
| `carriertracking number` | varchar(25) | Nullable |
| `orderqty` | smallint | |
| `productid` | INT FK | → `production.product` (via specialofferproduct) |
| `specialofferid` | INT FK | → `sales.specialofferproduct` |
| `unitprice` | numeric | Actual selling price |
| `unitpricediscount` | numeric | Discount fraction (0.0–1.0) |
| `modifieddate` | TIMESTAMP | |

**Note:** `linetotal = unitprice * (1.0 - unitpricediscount) * orderqty` is computed, not stored.

#### `sales.salesorderheadersalesreason`
| Column | Type | Notes |
|--------|------|-------|
| `salesorderid` | INT PK/FK | → `sales.salesorderheader` |
| `salesreasonid` | INT PK/FK | → `sales.salesreason` |
| `modifieddate` | TIMESTAMP | |

#### `sales.salesreason`
| Column | Type | Notes |
|--------|------|-------|
| `salesreasonid` | SERIAL PK | |
| `name` | varchar(50) | E.g., `Price`, `Quality`, `Manufacturer` |
| `reasontype` | varchar(50) | Category: `Other`, `Promotion`, `Marketing` |
| `modifieddate` | TIMESTAMP | |

#### `sales.specialoffer`
| Column | Type | Notes |
|--------|------|-------|
| `specialofferid` | SERIAL PK | |
| `description` | varchar(255) | Offer description |
| `discountpct` | numeric | Discount percentage |
| `type` | varchar(50) | E.g., `Seasonal Discount`, `Volume Discount` |
| `category` | varchar(50) | `Reseller` or `Customer` |
| `startdate` | TIMESTAMP | |
| `enddate` | TIMESTAMP | |
| `minqty` | INT | Minimum qualifying quantity |
| `maxqty` | INT | Nullable |
| `modifieddate` | TIMESTAMP | |

#### `sales.specialofferproduct`
Links special offers to eligible products.
| Column | Type | Notes |
|--------|------|-------|
| `specialofferid` | INT PK/FK | → `sales.specialoffer` |
| `productid` | INT PK/FK | → `production.product` |
| `modifieddate` | TIMESTAMP | |

#### `sales.creditcard`
| Column | Type | Notes |
|--------|------|-------|
| `creditcardid` | SERIAL PK | |
| `cardtype` | varchar(50) | `Vista`, `Distinguish`, `SuperiorCard`, `ColonialVoice` |
| `cardnumber` | varchar(25) | |
| `expmonth` | smallint | |
| `expyear` | smallint | |
| `modifieddate` | TIMESTAMP | |

#### `sales.personcreditcard`
| Column | Type | Notes |
|--------|------|-------|
| `businessentityid` | INT PK/FK | → `person.person` |
| `creditcardid` | INT PK/FK | → `sales.creditcard` |
| `modifieddate` | TIMESTAMP | |

#### `sales.currency`
| Column | Type | Notes |
|--------|------|-------|
| `currencycode` | char(3) PK | ISO currency code (e.g., `USD`, `EUR`) |
| `name` | varchar(50) | Currency name |
| `modifieddate` | TIMESTAMP | |

#### `sales.currencyrate`
| Column | Type | Notes |
|--------|------|-------|
| `currencyrateid` | SERIAL PK | |
| `currencyratedate` | TIMESTAMP | Date of rate |
| `fromcurrencycode` | char(3) FK | → `sales.currency` |
| `tocurrencycode` | char(3) FK | → `sales.currency` |
| `averagerate` | numeric | Day's average rate |
| `endofdayrate` | numeric | Closing rate |
| `modifieddate` | TIMESTAMP | |

#### `sales.countryregioncurrency`
| Column | Type | Notes |
|--------|------|-------|
| `countryregioncode` | varchar(3) PK/FK | → `person.countryregion` |
| `currencycode` | char(3) PK/FK | → `sales.currency` |
| `modifieddate` | TIMESTAMP | |

#### `sales.salestaxrate`
| Column | Type | Notes |
|--------|------|-------|
| `salestaxrateid` | SERIAL PK | |
| `stateprovinceid` | INT FK | → `person.stateprovince` |
| `taxtype` | smallint | `1`=Retail, `2`=Wholesale, `3`=All transactions |
| `taxrate` | numeric | |
| `name` | varchar(50) | Tax rate description |
| `modifieddate` | TIMESTAMP | |

#### `sales.shoppingcartitem`
Active (unpurchased) cart items.
| Column | Type | Notes |
|--------|------|-------|
| `shoppingcartitemid` | SERIAL PK | |
| `shoppingcartid` | varchar(50) | Session/cart identifier |
| `quantity` | INT | Default 1 |
| `productid` | INT FK | → `production.product` |
| `datecreated` | TIMESTAMP | |
| `modifieddate` | TIMESTAMP | |

---

## 4. FOREIGN KEY RELATIONSHIP MAP

```
BusinessEntityID (shared identity key)
├── person.businessentity.businessentityid  (root)
│   ├── person.person.businessentityid
│   │   ├── humanresources.employee.businessentityid
│   │   │   ├── sales.salesperson.businessentityid
│   │   │   └── purchasing.purchaseorderheader.employeeid
│   │   └── sales.customer.personid
│   ├── sales.store.businessentityid
│   │   └── sales.customer.storeid
│   └── purchasing.vendor.businessentityid

Product Hierarchy
production.productcategory
└── production.productsubcategory
    └── production.product
        ├── production.productmodel
        ├── production.productinventory → production.location
        ├── production.billofmaterials (self-join: assembly → component)
        ├── sales.salesorderdetail → sales.salesorderheader
        ├── purchasing.purchaseorderdetail → purchasing.purchaseorderheader
        └── production.workorder

Sales Hierarchy
sales.salesorderheader
├── sales.customer → (person.person | sales.store)
├── sales.salesperson → humanresources.employee → person.person
├── sales.salesterritory
├── person.address (bill-to and ship-to)
├── purchasing.shipmethod
├── sales.creditcard
└── sales.salesorderdetail
    └── production.product (via sales.specialofferproduct)

Address Resolution
person.address
└── person.stateprovince
    └── person.countryregion

person.businessentityaddress  (links entity ↔ address ↔ type)
```

---

## 5. COMMON JOIN PATHS (Copy-Paste Ready)

### Get full person name + email + phone
```sql
SELECT p.firstname, p.lastname, ea.emailaddress, pp.phonenumber, pnt.name AS phonetype
FROM person.person p
LEFT JOIN person.emailaddress ea ON p.businessentityid = ea.businessentityid
LEFT JOIN person.personphone pp ON p.businessentityid = pp.businessentityid
LEFT JOIN person.phonenumbertype pnt ON pp.phonenumbertypeid = pnt.phonenumbertypeid
```

### Get employee with department (current only)
```sql
SELECT e.businessentityid, p.firstname, p.lastname, e.jobtitle, d.name AS department, d.groupname
FROM humanresources.employee e
JOIN person.person p ON e.businessentityid = p.businessentityid
JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
JOIN humanresources.department d ON edh.departmentid = d.departmentid
WHERE edh.enddate IS NULL
```

### Get employee current pay rate
```sql
SELECT e.businessentityid, p.firstname, p.lastname, eph.rate, eph.payfrequency
FROM humanresources.employee e
JOIN person.person p ON e.businessentityid = p.businessentityid
JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
WHERE eph.ratechangedate = (
    SELECT MAX(ratechangedate)
    FROM humanresources.employeepayhistory
    WHERE businessentityid = e.businessentityid
)
```

### Get product with category + subcategory
```sql
SELECT p.productid, p.name, pc.name AS category, psc.name AS subcategory, p.listprice
FROM production.product p
LEFT JOIN production.productsubcategory psc ON p.productsubcategoryid = psc.productsubcategoryid
LEFT JOIN production.productcategory pc ON psc.productcategoryid = pc.productcategoryid
```

### Get sales order with customer + rep info
```sql
SELECT soh.salesorderid, soh.orderdate, soh.totaldue,
       p.firstname || ' ' || p.lastname AS customer_name,
       sp_p.firstname || ' ' || sp_p.lastname AS salesperson_name,
       st.name AS territory
FROM sales.salesorderheader soh
JOIN sales.customer c ON soh.customerid = c.customerid
LEFT JOIN person.person p ON c.personid = p.businessentityid
LEFT JOIN sales.salesperson sp ON soh.salespersonid = sp.businessentityid
LEFT JOIN person.person sp_p ON sp.businessentityid = sp_p.businessentityid
LEFT JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
```

### Get sales order line items with product detail
```sql
SELECT soh.salesorderid, soh.orderdate,
       prod.name AS product, sod.orderqty, sod.unitprice, sod.unitpricediscount,
       ROUND(sod.unitprice * (1 - sod.unitpricediscount) * sod.orderqty, 2) AS linetotal
FROM sales.salesorderheader soh
JOIN sales.salesorderdetail sod ON soh.salesorderid = sod.salesorderid
JOIN production.product prod ON sod.productid = prod.productid
```

### Get vendor with products supplied
```sql
SELECT v.name AS vendor, p.name AS product, pv.standardprice, pv.averageleadtime
FROM purchasing.vendor v
JOIN purchasing.productvendor pv ON v.businessentityid = pv.businessentityid
JOIN production.product p ON pv.productid = p.productid
WHERE v.activeflag = true
```

### Get address with full location
```sql
SELECT a.addressline1, a.city, sp.name AS state, cr.name AS country, a.postalcode
FROM person.address a
JOIN person.stateprovince sp ON a.stateprovinceid = sp.stateprovinceid
JOIN person.countryregion cr ON sp.countryregioncode = cr.countryregioncode
```

---

## 6. IMPORTANT COMPUTED FIELDS (NOT STORED)

These are calculated at query time — never stored as columns:

| Concept | Formula |
|---------|---------|
| Sales line total | `unitprice * (1.0 - unitpricediscount) * orderqty` |
| Purchase line total | `orderqty * unitprice` |
| Stocked qty (purchase) | `receivedqty - rejectedqty` |
| Sales order total | `subtotal + taxamt + freight` |
| Purchase order total | `subtotal + taxamt + freight` |
| Current employee department | `WHERE enddate IS NULL` in `employeedepartmenthistory` |
| Current employee pay | MAX(`ratechangedate`) per employee in `employeepayhistory` |
| Current product price | `WHERE enddate IS NULL` in `productlistpricehistory` |
| Currently active product | `WHERE sellenddate IS NULL AND discontinueddate IS NULL` |

---

## 7. ENUM / CODE FIELD REFERENCE

| Table | Column | Values |
|-------|--------|--------|
| `person.person` | `persontype` | `SC`=Store Contact, `IN`=Individual Customer, `SP`=Sales Person, `EM`=Employee, `VC`=Vendor Contact, `GC`=General Contact |
| `humanresources.employee` | `maritalstatus` | `M`=Married, `S`=Single |
| `humanresources.employee` | `gender` | `M`=Male, `F`=Female |
| `humanresources.employee` | `salariedflag` | `true`=Salaried, `false`=Hourly |
| `humanresources.employeepayhistory` | `payfrequency` | `1`=Monthly, `2`=Biweekly |
| `production.product` | `productline` | `R`=Road, `M`=Mountain, `T`=Touring, `S`=Standard |
| `production.product` | `class` | `H`=High, `M`=Medium, `L`=Low |
| `production.product` | `style` | `W`=Womens, `M`=Mens, `U`=Universal |
| `production.document` | `status` | `1`=Pending, `2`=Approved, `3`=Obsolete |
| `purchasing.purchaseorderheader` | `status` | `1`=Pending, `2`=Approved, `3`=Rejected, `4`=Complete |
| `purchasing.vendor` | `creditrating` | `1`=Superior, `2`=Excellent, `3`=Above avg, `4`=Average, `5`=Below avg |
| `sales.salesorderheader` | `status` | `1`=In process, `2`=Approved, `3`=Backordered, `4`=Rejected, `5`=Shipped, `6`=Cancelled |
| `sales.salesorderheader` | `onlineorderflag` | `true`=Online, `false`=Sales rep |
| `sales.salestaxrate` | `taxtype` | `1`=Retail, `2`=Wholesale, `3`=All |
| `sales.specialoffer` | `category` | `Reseller`, `Customer` |
| `production.transactionhistory` | `transactiontype` | `W`=WorkOrder, `S`=SalesOrder, `P`=PurchaseOrder |

---

## 8. AVAILABLE VIEWS (Use for Convenience)

### Semantic Views (pre-built joins)

| View | What it gives you |
|------|-------------------|
| `humanresources.vEmployee` | Employee + person + address + contact info |
| `humanresources.vEmployeeDepartment` | Employee + current department |
| `humanresources.vEmployeeDepartmentHistory` | Employee + all department history |
| `sales.vSalesPerson` | Sales rep + person + address + territory + quotas |
| `sales.vIndividualCustomer` | Individual customer + address + contact |
| `sales.vStoreWithDemographics` | Store + parsed XML demographic data |
| `sales.vStoreWithContacts` | Store + contact persons |
| `sales.vStoreWithAddresses` | Store + addresses |
| `purchasing.vVendorWithContacts` | Vendor + contacts |
| `purchasing.vVendorWithAddresses` | Vendor + addresses |
| `production.vProductAndDescription` | Product + model + description (materialized, multi-language) |
| `production.vProductModelCatalogDescription` | Product model XML catalog parsed into columns |
| `production.vProductModelInstructions` | Manufacturing instructions parsed into steps |
| `sales.vSalesPersonSalesByFiscalYears` | PIVOT: sales per rep per fiscal year (2012/2013/2014) |
| `person.vStateProvinceCountryRegion` | State + country (materialized) |
| `person.vAdditionalContactInfo` | Parsed XML contact info |
| `sales.vPersonDemographics` | Parsed XML customer survey data |
| `humanresources.vJobCandidate` | Job candidate + parsed resume XML |
| `humanresources.vJobCandidateEmployment` | Candidate employment history from XML |
| `humanresources.vJobCandidateEducation` | Candidate education history from XML |

### Convenience Shorthand Views (schema aliases)

| Shorthand | Full table |
|-----------|-----------|
| `pe.p` | `person.person` (+ `id` alias for `businessentityid`) |
| `pe.a` | `person.address` |
| `pe.sp` | `person.stateprovince` |
| `pe.cr` | `person.countryregion` |
| `pe.e` | `person.emailaddress` |
| `hr.e` | `humanresources.employee` |
| `hr.d` | `humanresources.department` |
| `hr.edh` | `humanresources.employeedepartmenthistory` |
| `hr.eph` | `humanresources.employeepayhistory` |
| `pr.p` | `production.product` |
| `pr.pc` | `production.productcategory` |
| `pr.psc` | `production.productsubcategory` |
| `pr.pm` | `production.productmodel` |
| `pr.pi` | `production.productinventory` |
| `pr.w` | `production.workorder` |
| `pu.v` | `purchasing.vendor` |
| `pu.poh` | `purchasing.purchaseorderheader` |
| `pu.pod` | `purchasing.purchaseorderdetail` |
| `sa.soh` | `sales.salesorderheader` |
| `sa.sod` | `sales.salesorderdetail` |
| `sa.c` | `sales.customer` |
| `sa.sp` | `sales.salesperson` |
| `sa.st` | `sales.salesterritory` |
| `sa.s` | `sales.store` |

---

## 9. COMPLEX QUERY PATTERNS & TEMPLATES

### Top N products by sales revenue
```sql
SELECT prod.name, SUM(sod.orderqty * sod.unitprice * (1 - sod.unitpricediscount)) AS revenue
FROM sales.salesorderdetail sod
JOIN production.product prod ON sod.productid = prod.productid
JOIN sales.salesorderheader soh ON sod.salesorderid = soh.salesorderid
WHERE soh.status = 5  -- Shipped
GROUP BY prod.productid, prod.name
ORDER BY revenue DESC
LIMIT 10;
```

### Sales by territory and year
```sql
SELECT st.name AS territory, st.group,
       EXTRACT(YEAR FROM soh.orderdate) AS year,
       SUM(soh.subtotal) AS total_sales,
       COUNT(DISTINCT soh.salesorderid) AS order_count
FROM sales.salesorderheader soh
JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
WHERE soh.status = 5
GROUP BY st.territoryid, st.name, st.group, EXTRACT(YEAR FROM soh.orderdate)
ORDER BY year, total_sales DESC;
```

### Employee salary ranking by department
```sql
WITH current_pay AS (
    SELECT eph.businessentityid,
           eph.rate,
           ROW_NUMBER() OVER (PARTITION BY eph.businessentityid ORDER BY eph.ratechangedate DESC) AS rn
    FROM humanresources.employeepayhistory eph
),
current_dept AS (
    SELECT edh.businessentityid, edh.departmentid
    FROM humanresources.employeedepartmenthistory edh
    WHERE edh.enddate IS NULL
)
SELECT d.name AS department,
       p.firstname || ' ' || p.lastname AS employee,
       e.jobtitle,
       cp.rate,
       RANK() OVER (PARTITION BY d.departmentid ORDER BY cp.rate DESC) AS salary_rank
FROM humanresources.employee e
JOIN person.person p ON e.businessentityid = p.businessentityid
JOIN current_dept cd ON e.businessentityid = cd.businessentityid
JOIN humanresources.department d ON cd.departmentid = d.departmentid
JOIN current_pay cp ON e.businessentityid = cp.businessentityid AND cp.rn = 1
ORDER BY d.name, salary_rank;
```

### Product inventory below reorder point
```sql
SELECT p.name, p.productnumber, p.reorderpoint,
       COALESCE(SUM(pi.quantity), 0) AS total_stock,
       p.reorderpoint - COALESCE(SUM(pi.quantity), 0) AS deficit
FROM production.product p
LEFT JOIN production.productinventory pi ON p.productid = pi.productid
WHERE p.finishedgoodsflag = true
GROUP BY p.productid, p.name, p.productnumber, p.reorderpoint
HAVING COALESCE(SUM(pi.quantity), 0) < p.reorderpoint
ORDER BY deficit DESC;
```

### Customer lifetime value (CLV) — top customers
```sql
SELECT p.firstname || ' ' || p.lastname AS customer_name,
       COUNT(DISTINCT soh.salesorderid) AS total_orders,
       SUM(soh.subtotal) AS lifetime_value,
       MIN(soh.orderdate) AS first_order,
       MAX(soh.orderdate) AS last_order,
       AVG(soh.subtotal) AS avg_order_value
FROM sales.customer c
JOIN person.person p ON c.personid = p.businessentityid
JOIN sales.salesorderheader soh ON c.customerid = soh.customerid
WHERE soh.status = 5
GROUP BY c.customerid, p.firstname, p.lastname
ORDER BY lifetime_value DESC
LIMIT 20;
```

### Month-over-month sales growth (window function)
```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', orderdate) AS month,
           SUM(subtotal) AS monthly_sales
    FROM sales.salesorderheader
    WHERE status = 5
    GROUP BY DATE_TRUNC('month', orderdate)
)
SELECT month,
       monthly_sales,
       LAG(monthly_sales) OVER (ORDER BY month) AS prev_month_sales,
       ROUND((monthly_sales - LAG(monthly_sales) OVER (ORDER BY month))
             / NULLIF(LAG(monthly_sales) OVER (ORDER BY month), 0) * 100, 2) AS growth_pct
FROM monthly
ORDER BY month;
```

### Sales rep performance vs quota
```sql
SELECT p.firstname || ' ' || p.lastname AS rep_name,
       st.name AS territory,
       sp.salesquota,
       sp.salesytd,
       sp.salesytd - COALESCE(sp.salesquota, 0) AS vs_quota,
       CASE
           WHEN sp.salesquota IS NULL THEN 'No Quota'
           WHEN sp.salesytd >= sp.salesquota THEN 'On Target'
           ELSE 'Below Target'
       END AS status
FROM sales.salesperson sp
JOIN humanresources.employee e ON sp.businessentityid = e.businessentityid
JOIN person.person p ON e.businessentityid = p.businessentityid
LEFT JOIN sales.salesterritory st ON sp.territoryid = st.territoryid
WHERE e.currentflag = true
ORDER BY vs_quota DESC;
```

### Bill of Materials — recursive CTE (product tree)
```sql
WITH RECURSIVE bom_tree AS (
    -- Root assemblies
    SELECT bom.productassemblyid, bom.componentid, bom.bomlevel,
           bom.perassemblyqty, prod.name AS component_name
    FROM production.billofmaterials bom
    JOIN production.product prod ON bom.componentid = prod.productid
    WHERE bom.productassemblyid = :target_product_id
      AND bom.enddate IS NULL
    UNION ALL
    -- Child components
    SELECT bom.productassemblyid, bom.componentid, bom.bomlevel,
           bt.perassemblyqty * bom.perassemblyqty AS perassemblyqty,
           prod.name AS component_name
    FROM production.billofmaterials bom
    JOIN production.product prod ON bom.componentid = prod.productid
    JOIN bom_tree bt ON bom.productassemblyid = bt.componentid
    WHERE bom.enddate IS NULL
)
SELECT bomlevel, component_name, SUM(perassemblyqty) AS total_qty_needed
FROM bom_tree
GROUP BY bomlevel, component_name
ORDER BY bomlevel, component_name;
```

### Vendor purchase analysis with lead time
```sql
SELECT v.name AS vendor, v.creditrating,
       COUNT(DISTINCT poh.purchaseorderid) AS total_orders,
       SUM(poh.subtotal) AS total_spent,
       AVG(pv.averageleadtime) AS avg_lead_days,
       COUNT(DISTINCT pv.productid) AS products_supplied
FROM purchasing.vendor v
JOIN purchasing.purchaseorderheader poh ON v.businessentityid = poh.vendorid
JOIN purchasing.productvendor pv ON v.businessentityid = pv.businessentityid
WHERE v.activeflag = true
GROUP BY v.businessentityid, v.name, v.creditrating
ORDER BY total_spent DESC;
```

### Products never sold
```sql
SELECT p.productid, p.name, p.productnumber, p.listprice, p.sellstartdate
FROM production.product p
WHERE p.finishedgoodsflag = true
  AND p.sellenddate IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM sales.salesorderdetail sod WHERE sod.productid = p.productid
  );
```

### Cross-sell: customers who bought X also bought
```sql
WITH buyers_of_x AS (
    SELECT DISTINCT soh.customerid
    FROM sales.salesorderdetail sod
    JOIN sales.salesorderheader soh ON sod.salesorderid = soh.salesorderid
    WHERE sod.productid = :product_id_x
)
SELECT prod.name, COUNT(DISTINCT soh.customerid) AS co_buyers,
       ROUND(COUNT(DISTINCT soh.customerid)::numeric / (SELECT COUNT(*) FROM buyers_of_x) * 100, 1) AS pct
FROM sales.salesorderdetail sod
JOIN sales.salesorderheader soh ON sod.salesorderid = soh.salesorderid
JOIN production.product prod ON sod.productid = prod.productid
WHERE soh.customerid IN (SELECT customerid FROM buyers_of_x)
  AND sod.productid != :product_id_x
GROUP BY prod.productid, prod.name
ORDER BY co_buyers DESC
LIMIT 10;
```

---

## 10. SYSTEM PROMPT — PASTE THIS WHEN CALLING THE LLM

```
You are an expert PostgreSQL query generator for the AdventureWorks database hosted on Supabase.

RULES:
1. Always use fully qualified table names: schema.tablename (e.g., sales.salesorderheader, not just salesorderheader).
2. Use lowercase for all schema and table names.
3. Column names are case-insensitive in PostgreSQL but prefer lowercase.
4. For money/price values, use numeric — not the money type.
5. For date operations, use PostgreSQL functions: DATE_TRUNC(), EXTRACT(), NOW(), INTERVAL.
6. Computed fields like linetotal, totaldue, stockedqty are NOT stored — compute them inline.
7. "Current" records pattern:
   - Current department: WHERE edh.enddate IS NULL
   - Current pay rate: MAX(ratechangedate) per employee
   - Current price: WHERE enddate IS NULL in productlistpricehistory
   - Active products: WHERE sellenddate IS NULL AND discontinueddate IS NULL
8. Boolean fields: use TRUE/FALSE (not 1/0).
9. For complex aggregations, use CTEs (WITH clause) for readability.
10. When joining to person.person from employee/customer/vendor, always join on businessentityid.
11. Sales orders: status=5 means Shipped. Use this when asking for "completed" or "shipped" orders.
12. Employees: currentflag=TRUE means active. Use this when filtering for current staff.
13. Vendors: activeflag=TRUE means active.
14. Always add ORDER BY for any query requesting "top N" or ranked results.
15. Use window functions (RANK, ROW_NUMBER, LAG, LEAD, SUM OVER) for rankings and trends.

DATABASE CONTEXT:
[PASTE THE FULL SCHEMA SECTION FROM THIS FILE HERE — SECTIONS 3 THROUGH 9]
```

---

## 11. SUPABASE-SPECIFIC NOTES

- **Connection:** Use the Supabase connection URI with `?sslmode=require` appended
- **Row-Level Security (RLS):** If RLS is enabled on tables, queries via the anon/service key behave differently. Use the service role key for full access in your NL-to-SQL backend.
- **Schema search path:** By default, Supabase sets `search_path=public`. Since all AdventureWorks tables are in custom schemas, **always qualify with schema name** (e.g., `sales.salesorderheader`, not just `salesorderheader`).
- **Materialized views** (`production.vProductAndDescription`, `person.vStateProvinceCountryRegion`) need manual refresh if underlying data changes: `REFRESH MATERIALIZED VIEW <view_name>;`
- **UUID columns** (`rowguid`) are generated — do not insert manually.
- **SERIAL columns** auto-increment — omit from INSERT statements.

---

## 12. QUICK INTROSPECTION QUERIES (Run these on your live DB)

```sql
-- All tables with row counts
SELECT schemaname, tablename,
       (xpath('/row/c/text()', query_to_xml('SELECT COUNT(*) AS c FROM ' || schemaname || '.' || tablename, false, true, '')))[1]::text::int AS row_count
FROM pg_tables
WHERE schemaname IN ('person','humanresources','production','purchasing','sales')
ORDER BY schemaname, tablename;

-- All foreign keys
SELECT tc.table_schema, tc.table_name, kcu.column_name,
       ccu.table_schema AS ref_schema, ccu.table_name AS ref_table, ccu.column_name AS ref_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema IN ('person','humanresources','production','purchasing','sales')
ORDER BY tc.table_schema, tc.table_name;

-- All columns with types
SELECT table_schema, table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema IN ('person','humanresources','production','purchasing','sales')
ORDER BY table_schema, table_name, ordinal_position;
```

"""
