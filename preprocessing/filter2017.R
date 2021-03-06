library(edgeR)

data2017 <- read.table("data/input/2017/GSE89843_TEP_Count_Matrix.txt", header=TRUE)
count_data <- data2017[,-1]
rownames(count_data) <- data2017[,1]

# library(openxlsx)
# patient_info <- read.xlsx('data/input/2017/mmc2.xlsx', rows=c(3:782), cols=c(2:13), sep.names='_')
# 
# healthy_status <- data.frame(factor(patient_info$Classification_group))
# rownames(healthy_status) <- gsub('-', '.', patient_info$Sample_name)
# colnames(healthy_status) = "status"

#the below disease_data contains repeats with 'Please note that the mapped and counted intron-spanning reads from both files corresponding to this sample were merged in silico to yield sufficient mapped reads for further analyses.'
# library(GEOquery)
# gsm <- getGEO(filename = 'data/input/2017/GSE89843_series_matrix.txt.gz')
# disease_data <- data.frame(gsm$description, gsm$characteristics_ch1)
# colnames(disease_data) <- c('sample_name', 'disease')


disease_data <- data.frame(colnames(count_data))
colnames(disease_data) <- 'sample_name'
disease_data['disease_status'] <- disease_data$sample_name
levels(disease_data$disease_status) <- c(levels(disease_data$disease_status), 'Cancer', 'NonCancer')
disease_data$disease_status[grepl('NSCLC', disease_data$disease_status)] <- 'Cancer'
disease_data$disease_status[grepl('LGG', disease_data$disease_status)] <- 'Cancer'
disease_data$disease_status[!grepl('Cancer', disease_data$disease_status)] <- 'NonCancer'
disease_data$disease_status <- factor(disease_data$disease_status)



# filtering count_data
# cpm_data <- cpm(count_data)

# colnames(count_data[colSums(count_data) == min(colSums(count_data))])

# min_total_count_genes <- sort((colSums(count_data)))[1:4]
# par(mfrow = c(2, 2))
# 
# for(i in c(1:length(min_total_count_genes))){
#   gene <- names(min_total_count_genes)[i]
#   plot(cpm_data[, gene], count_data[, gene], main=gene, pch = i, ylim = c(0, 50), xlim = c(0, 1000))
# }
# 
# threshold <- cpm_data > 1
# keep <- rowSums(threshold) >= 377
# summary(keep)
# filtered_data <- count_data[keep, ]

keep <- filterByExpr(count_data)
filtered_data <- count_data[keep, ]

y <- DGEList(filtered_data)
y <- calcNormFactors(y)
group <- disease_data$disease_status

design <- model.matrix(~ 0 + group)
colnames(design) <- levels(group)

par(mfrow=c(1,1))
v <- voom(y,design,plot = TRUE)

normalized_data <- v$E
colnames(normalized_data) <- disease_data$disease_status

write.csv(normalized_data, "data/output/normalized_NSCLC_data.csv")

dim(normalized_data)
dim(count_data)
summary(disease_data$disease_status)