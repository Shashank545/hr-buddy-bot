type ParsedSupportingContentItem = {
    id: string;
    score: number;
    title: string;
    category: string;
    content: string;
};

export function parseSupportingContentItem(item: any): ParsedSupportingContentItem {
    // Assumes the item starts with the file name followed by : and the content.
    // Example: "sdp_corporate.pdf: this is the content that follows".
    // const parts = item.split(": ");
    const id = item.id;
    const score = item.score;
    const title = item.title;
    const category = item.category;
    const content = item.content;

    return {
        id,
        score,
        title,
        category,
        content,
    };
}
