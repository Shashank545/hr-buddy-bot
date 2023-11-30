
export const enum Approaches {
    RetrieveRead = "rr",
    RetrieveReformulateRetrieveRead = "rrrr",
    RetrieveReadRead = "rrr",
    RetrieveReadRetry = "rrrt",
}

export const enum Deployments {
    Gpt35Turbo = "gpt-35-turbo",
    Gpt4 = "gpt-4"
}

export enum ACSIndex {
    IFRS = "ifrs",
    JGAAP = "jgaap",
}

export enum SearchOptions {
    BM25 = "BM25",
    Semantic = "Semantic Search",
    Vector = "Embeddings",
    VectorBM25 = "VectorBM25",
    VectorSemantic = "VectorSemantic"
}

export type AskRequestOverrides = {
    semanticRanker?: boolean;
    semanticCaptions?: boolean;
    excludeCategory?: string;
    top?: number;
    temperature?: number;
    promptTemplate?: string;
    promptTemplatePrefix?: string;
    promptTemplateSuffix?: string;
    suggestFollowupQuestions?: boolean;
    searchOption?: number;
};

export type AskRequest = {
    question: string;
    approach: Approaches;
    deployment: Deployments;
    index: ACSIndex;
    overrides?: AskRequestOverrides;
};

export type AskResponse = {
    approach: Approaches;
    answer: string;
    monitoring: {
        time: {
            total: string;
            items: any[];
        },
        cost: {
            total: string;
            items: any[];
        },
        usage: {
            label: string;
            value: any;
        }[];
    };
    thoughts: {
        label: string;
        value: any;
    }[];
    data_points: string[];
    error?: string;
};
