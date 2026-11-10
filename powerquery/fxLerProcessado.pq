// Lê uma tabela já tratada pelo ETL Python (data/processado, ';', UTF-8).
// O Power BI só modela e visualiza: as regras de negócio ficam no ETL testado.
(nome as text) as table =>
let
    Origem   = Csv.Document(File.Contents(PastaProcessado & nome & ".csv"), [Delimiter = ";", Encoding = 65001]),
    Promover = Table.PromoteHeaders(Origem, [PromoteAllScalars = true])
in
    Promover
